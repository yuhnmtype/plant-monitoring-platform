"""Integration tests in a throwaway schema. Skipped, visibly, when the database is down."""

import psycopg
import pytest

from plantmon.core.migrate import migrate
from plantmon.core.store import count_rows, read_series, replace_run
from plantmon.sim.schedule import generate_schedule
from plantmon.sim.signals import context_states, simulate, split_bounds, timestamps

RUN_TABLES = (
    "run_splits",
    "sensors",
    "readings",
    "context_readings",
    "incident_labels",
    "sensor_state_ranges",
)


@pytest.fixture
def conn(db):
    migrate(db)
    return db


def _store(conn, profile, seed=42, sha="hash-a"):
    """Store one run and return (times, run_id)."""
    times = timestamps(profile)
    run_id = replace_run(
        conn,
        profile,
        sha,
        seed,
        times,
        simulate(profile, seed).reported,
        context_states(profile, times),
        generate_schedule(profile, seed),
        split_bounds(profile),
    )
    return times, run_id


def _dump(conn, run_id):
    """Every stored row of one run, in a fixed order."""
    queries = {
        "run_splits": "SELECT split, start_ts, end_ts FROM run_splits WHERE run_id = %s ORDER BY 1",
        "sensors": "SELECT id, asset, kind, unit, nominal_low, nominal_high FROM sensors"
        " WHERE run_id = %s ORDER BY 1",
        "readings": "SELECT sensor_id, ts, value FROM readings WHERE run_id = %s ORDER BY 1, 2",
        "context": "SELECT ts, state FROM context_readings WHERE run_id = %s ORDER BY 1",
        "labels": "SELECT start_ts, end_ts, class_id, incident_type, split FROM incident_labels"
        " WHERE run_id = %s ORDER BY 1",
        "ranges": "SELECT sensor_id, state, low, high FROM sensor_state_ranges"
        " WHERE run_id = %s ORDER BY 1, 2",
    }
    return {name: conn.execute(q, (run_id,)).fetchall() for name, q in queries.items()}


def _run_ids(conn):
    return [r[0] for r in conn.execute("SELECT run_id FROM runs ORDER BY run_id")]


def test_row_counts_match_sensors_times_samples(conn, profile):
    times, run_id = _store(conn, profile)
    assert count_rows(conn, "readings", run_id) == 2 * len(times)
    assert count_rows(conn, "context_readings", run_id) == len(times)
    assert count_rows(conn, "incident_labels", run_id) == 8
    assert count_rows(conn, "run_splits", run_id) == 3
    assert count_rows(conn, "sensors", run_id) == 2


def test_profile_without_context_stores_no_context_or_state_range_rows(conn, profile):
    del profile["context"]
    del profile["sensors"][0]["signal"]["state_offset"]
    _, run_id = _store(conn, profile)
    assert count_rows(conn, "context_readings", run_id) == 0
    assert count_rows(conn, "sensor_state_ranges", run_id) == 0


def test_run_splits_hold_the_profile_split_bounds(conn, profile):
    _, run_id = _store(conn, profile)
    stored = conn.execute(
        "SELECT split, start_ts, end_ts FROM run_splits WHERE run_id = %s ORDER BY start_ts",
        (run_id,),
    ).fetchall()
    assert stored == [(name, *bounds) for name, bounds in split_bounds(profile).items()]


def test_same_profile_seed_and_hash_replaces_only_its_own_run(conn, profile):
    _, first = _store(conn, profile, seed=42)
    _, second = _store(conn, profile, seed=43)
    first_before = _dump(conn, first)
    second_before = _dump(conn, second)

    profile["sensors"][1]["signal"]["base"] = 77  # same hash on purpose: the rows must be rewritten
    _, again = _store(conn, profile, seed=42)

    assert again == first
    assert _run_ids(conn) == [first, second]
    first_after = _dump(conn, first)
    assert first_after["readings"] != first_before["readings"]
    assert len(first_after["readings"]) == len(first_before["readings"])
    assert _dump(conn, second) == second_before


def test_another_seed_adds_a_run_and_leaves_the_first_unchanged(conn, profile):
    _, first = _store(conn, profile, seed=42)
    first_before = _dump(conn, first)
    _, second = _store(conn, profile, seed=43)
    assert second != first
    assert _run_ids(conn) == [first, second]
    assert _dump(conn, first) == first_before


def test_same_seed_with_a_changed_profile_hash_adds_a_run(conn, profile):
    _, first = _store(conn, profile, seed=42, sha="hash-a")
    first_before = _dump(conn, first)
    _, second = _store(conn, profile, seed=42, sha="hash-b")
    assert second != first
    assert _run_ids(conn) == [first, second]
    assert _dump(conn, first) == first_before


def test_deleting_a_run_removes_all_its_rows(conn, profile):
    _, run_id = _store(conn, profile)
    _, other = _store(conn, profile, seed=43)
    other_before = _dump(conn, other)
    assert all(count_rows(conn, table, run_id) > 0 for table in RUN_TABLES[:-1])

    conn.execute("DELETE FROM runs WHERE run_id = %s", (run_id,))
    assert [count_rows(conn, table, run_id) for table in RUN_TABLES] == [0] * len(RUN_TABLES)
    assert _dump(conn, other) == other_before


def test_stored_series_equals_the_reported_layer(conn, profile):
    profile["sensors"][0]["measurement_noise_std"] = 1.0
    times, run_id = _store(conn, profile)
    stored_times, stored_values = read_series(conn, run_id, "s1", times[-1])
    result = simulate(profile, 42)
    assert stored_times == times[:-1]
    assert stored_values == result.reported["s1"].tolist()[:-1]
    assert stored_values != result.physical["s1"].tolist()[:-1]


def test_a_state_left_out_is_stored_with_the_sensor_nominal_range(conn, profile):
    profile["sensors"][0]["nominal_range_by_state"] = {"alpha": [10, 20]}
    _, run_id = _store(conn, profile)
    assert _dump(conn, run_id)["ranges"] == [
        ("s1", "alpha", 10, 20),
        ("s1", "beta", 0, 100),  # left out: the sensor's nominal_range
        ("s2", "alpha", 0, 100),
        ("s2", "beta", 0, 100),
    ]


def test_a_follower_can_declare_a_range_for_a_state(conn, profile):
    profile["sensors"].append(
        {
            "id": "s3",
            "asset": "a1",
            "kind": "measurement",
            "unit": "u",
            "nominal_range": [0, 500],
            "nominal_range_by_state": {"beta": [30, 60]},
            "follows": {"source": "s1", "gain": 2.0, "offset": 1.0},
        }
    )
    _, run_id = _store(conn, profile)
    ranges = [r for r in _dump(conn, run_id)["ranges"] if r[0] == "s3"]
    assert ranges == [("s3", "alpha", 0, 500), ("s3", "beta", 30, 60)]


def test_database_refuses_a_range_with_low_not_below_high(conn, profile):
    _, run_id = _store(conn, profile)
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        conn.execute(
            "INSERT INTO sensor_state_ranges (run_id, sensor_id, state, low, high)"
            " VALUES (%s, 's1', 'gamma', 5, 5)",
            (run_id,),
        )


def test_database_refuses_data_not_marked_simulated(conn):
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        conn.execute(
            "INSERT INTO runs (profile_id, name, simulated, seed, profile_sha256, interval_minutes)"
            " VALUES ('p', 'not simulated', false, 0, 'x', 60)"
        )
