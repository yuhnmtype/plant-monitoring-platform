"""Data-quality checks in a throwaway schema, on a small clean run with deliberate corruptions."""

import contextlib
from pathlib import Path

import pytest

import plantmon.__main__ as demo_module
from plantmon.core.migrate import migrate
from plantmon.core.quality import run_checks
from plantmon.core.store import count_rows, replace_run
from plantmon.sim.schedule import generate_schedule
from plantmon.sim.signals import context_states, simulate, split_bounds, timestamps

CHECK_IDS = [
    "finite_values",
    "labels_in_split",
    "outside_splits",
    "regular_step",
    "sample_count",
]
PROFILE_IDS = sorted(p.parent.name for p in Path("profiles").glob("*/profile.yaml"))


@pytest.fixture
def clean_run(db, profile):
    """Store a small clean run and return (connection, run_id)."""
    migrate(db)
    times = timestamps(profile)
    run_id = replace_run(
        db,
        profile,
        "hash-a",
        42,
        times,
        simulate(profile, 42).reported,
        context_states(profile, times),
        generate_schedule(profile, 42),
        split_bounds(profile),
    )
    return db, run_id


def _by_id(results):
    return {r.check_id: r for r in results}


# Each corruption is plain SQL on a stored clean run: (check that must fail, SQL, violations).
# The fixture has a 60-minute step, splits of one month and 7 days between them.
CORRUPTIONS = {
    # The last reading of s1 in train is gone: the (s1, train) pair has one reading too few.
    # The rows before it still step by 60 minutes, so regular_step stays clean.
    "sample_count": (
        """
        DELETE FROM readings
        WHERE run_id = %(run_id)s AND sensor_id = 's1' AND ts = (
            SELECT max(x.ts) FROM readings x
            JOIN run_splits sp ON sp.run_id = x.run_id AND sp.split = 'train'
                AND x.ts >= sp.start_ts AND x.ts < sp.end_ts
            WHERE x.run_id = %(run_id)s AND x.sensor_id = 's1')
        """,
        1,
    ),
    # A reading in the middle of train moves 1 minute later and stays inside the split, so the
    # count is unchanged. Its own gap becomes 61 minutes and the next row's gap 59: 2 rows.
    "regular_step": (
        """
        UPDATE readings SET ts = ts + interval '1 minute'
        WHERE run_id = %(run_id)s AND sensor_id = 's1' AND ts = (
            SELECT start_ts + interval '10 hours' FROM run_splits
            WHERE run_id = %(run_id)s AND split = 'train')
        """,
        2,
    ),
    # One reading one day after train ends, inside the 7-day gap: 1 row. regular_step and
    # sample_count only look inside splits, so they ignore it.
    "outside_splits": (
        """
        INSERT INTO readings (run_id, sensor_id, ts, value)
        SELECT run_id, 's1', end_ts + interval '1 day', 1.0
        FROM run_splits WHERE run_id = %(run_id)s AND split = 'train'
        """,
        1,
    ),
    # The first label of the run ends one hour after the end of its split: 1 label.
    "labels_in_split": (
        """
        UPDATE incident_labels l SET end_ts = sp.end_ts + interval '1 hour'
        FROM run_splits sp
        WHERE sp.run_id = l.run_id AND sp.split = l.split AND l.run_id = %(run_id)s
          AND l.start_ts = (SELECT min(start_ts) FROM incident_labels
                            WHERE run_id = %(run_id)s)
        """,
        1,
    ),
}

# double precision accepts all three, so the type alone does not keep them out.
NON_FINITE = {"NaN": "'NaN'", "Infinity": "'Infinity'", "minus_Infinity": "'-Infinity'"}


def _non_finite(literal):
    """One reading of s2 in validation is set to a non-finite value: 1 row."""
    return f"""
        UPDATE readings SET value = {literal}::double precision
        WHERE run_id = %(run_id)s AND sensor_id = 's2' AND ts = (
            SELECT start_ts + interval '5 hours' FROM run_splits
            WHERE run_id = %(run_id)s AND split = 'validation')
        """


# (check that must fail, corruption SQL, expected violations), one case per corruption.
CASES = [
    pytest.param(check_id, *CORRUPTIONS[check_id], id=check_id)
    for check_id in CHECK_IDS
    if check_id != "finite_values"
]
CASES += [
    pytest.param("finite_values", _non_finite(literal), 1, id=f"finite_values-{name}")
    for name, literal in NON_FINITE.items()
]


def test_a_clean_run_passes_all_five_checks(clean_run):
    conn, run_id = clean_run
    results = run_checks(conn, run_id)
    assert [r.check_id for r in results] == CHECK_IDS
    assert [(r.passed, r.violations) for r in results] == [(True, 0)] * 5
    stored = conn.execute(
        "SELECT check_id, passed, violations FROM dq_results WHERE run_id = %s ORDER BY 1",
        (run_id,),
    ).fetchall()
    assert stored == [(check_id, True, 0) for check_id in CHECK_IDS]


def test_the_fixture_profile_has_a_gap_between_splits(clean_run):
    conn, run_id = clean_run
    ends_and_starts = conn.execute(
        "SELECT a.end_ts, b.start_ts FROM run_splits a, run_splits b"
        " WHERE a.run_id = %s AND b.run_id = a.run_id AND a.split = 'train'"
        " AND b.split = 'validation'",
        (run_id,),
    ).fetchone()
    assert ends_and_starts[0] < ends_and_starts[1]


@pytest.mark.parametrize(("check_id", "sql", "expected"), CASES)
def test_one_corruption_fails_its_check_and_the_other_four_pass(clean_run, check_id, sql, expected):
    conn, run_id = clean_run
    conn.execute(sql, {"run_id": run_id})
    results = _by_id(run_checks(conn, run_id))
    assert (results[check_id].passed, results[check_id].violations) == (False, expected)
    others = {k: (v.passed, v.violations) for k, v in results.items() if k != check_id}
    assert others == {k: (True, 0) for k in CHECK_IDS if k != check_id}


def test_outside_splits_counts_context_rows_too(clean_run):
    conn, run_id = clean_run
    conn.execute(
        "INSERT INTO context_readings (run_id, ts, state)"
        " SELECT run_id, end_ts + interval '1 day', 'alpha' FROM run_splits"
        " WHERE run_id = %s AND split = 'train'",
        (run_id,),
    )
    results = _by_id(run_checks(conn, run_id))
    assert results["outside_splits"].violations == 1
    assert sum(r.violations for r in results.values()) == 1


def test_a_second_check_run_rewrites_the_results(clean_run):
    conn, run_id = clean_run
    run_checks(conn, run_id)
    conn.execute(_non_finite("'NaN'"), {"run_id": run_id})
    run_checks(conn, run_id)
    stored = conn.execute(
        "SELECT check_id, passed, violations FROM dq_results WHERE run_id = %s ORDER BY 1",
        (run_id,),
    ).fetchall()
    assert len(stored) == 5
    assert ("finite_values", False, 1) in stored


@pytest.mark.parametrize("where", ["empty", "missing"])
def test_an_empty_or_missing_check_directory_fails_closed(clean_run, tmp_path, where):
    conn, run_id = clean_run
    directory = tmp_path if where == "empty" else tmp_path / "no_such_directory"
    with pytest.raises(ValueError, match=r"does not exist or holds no \*\.sql file") as error:
        run_checks(conn, run_id, directory)
    assert str(directory) in str(error.value)
    assert count_rows(conn, "dq_results", run_id) == 0


def test_a_check_that_does_not_return_one_integer_is_rejected(clean_run, tmp_path):
    conn, run_id = clean_run
    (tmp_path / "two_rows.sql").write_text("SELECT 1 UNION ALL SELECT 2", encoding="utf-8")
    with pytest.raises(ValueError, match="two_rows.sql must return exactly one integer"):
        run_checks(conn, run_id, tmp_path)


def test_rewriting_a_run_deletes_its_stale_results(clean_run, profile):
    conn, run_id = clean_run
    run_checks(conn, run_id)
    other = replace_run(conn, profile, "hash-b", 43, *_rows(profile, 43))  # must keep its results
    run_checks(conn, other)
    assert count_rows(conn, "dq_results", run_id) == 5

    again = replace_run(conn, profile, "hash-a", 42, *_rows(profile, 42))
    assert again == run_id
    assert count_rows(conn, "dq_results", run_id) == 0
    assert count_rows(conn, "dq_results", other) == 5


def _rows(profile, seed):
    times = timestamps(profile)
    return (
        times,
        simulate(profile, seed).reported,
        context_states(profile, times),
        generate_schedule(profile, seed),
        split_bounds(profile),
    )


def _run_demo(db, monkeypatch, tmp_path, profile_id, corrupt):
    """Run the real demo on a real profile in the throwaway schema. Return the exit code."""
    migrate(db)
    real_replace_run = demo_module.replace_run

    def replace_then_corrupt(*args, **kwargs):
        run_id = real_replace_run(*args, **kwargs)
        if corrupt:  # one NaN: the finite_values check must fail
            args[0].execute(
                "UPDATE readings SET value = 'NaN'::double precision WHERE run_id = %(r)s"
                " AND sensor_id = (SELECT min(id) FROM sensors WHERE run_id = %(r)s)"
                " AND ts = (SELECT min(ts) FROM readings WHERE run_id = %(r)s)",
                {"r": run_id},
            )
        return run_id

    monkeypatch.setattr(demo_module.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(demo_module, "connect", lambda: contextlib.nullcontext(db))
    monkeypatch.setattr(demo_module, "replace_run", replace_then_corrupt)
    monkeypatch.setattr(demo_module, "CHART_PATH", tmp_path / "chart.png")
    return demo_module.demo(profile_id, 42)


def test_at_least_one_repo_profile_is_demoed():
    assert PROFILE_IDS  # zero profiles must fail here, not silently collect no demo cases


@pytest.mark.parametrize("profile_id", PROFILE_IDS)
def test_demo_exits_zero_and_prints_five_passed_lines_on_a_clean_run(
    db, monkeypatch, tmp_path, capsys, profile_id
):
    assert _run_demo(db, monkeypatch, tmp_path, profile_id, corrupt=False) == 0
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("Data quality")]
    assert lines == [f"Data quality {check_id}: passed, violations 0" for check_id in CHECK_IDS]


@pytest.mark.parametrize("profile_id", PROFILE_IDS[:1])  # the first profile is enough here
def test_demo_exits_nonzero_but_still_writes_the_chart_when_a_check_fails(
    db, monkeypatch, tmp_path, capsys, profile_id
):
    assert _run_demo(db, monkeypatch, tmp_path, profile_id, corrupt=True) == 1
    out = capsys.readouterr().out
    assert "Data quality finite_values: FAILED, violations 1" in out
    assert (tmp_path / "chart.png").exists()
