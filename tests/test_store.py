"""Integration tests against the compose database. Skipped, visibly, when it is not running."""

import psycopg
import pytest

from plantmon.core.store import apply_schema, connect, count_rows, read_series, replace_run
from plantmon.sim.schedule import generate_schedule
from plantmon.sim.signals import context_states, simulate, timestamps


@pytest.fixture
def conn(profile):
    try:
        connection = connect()
    except psycopg.OperationalError:
        pytest.skip("database not running: docker compose up -d --wait db")
    with connection:
        apply_schema(connection)
        yield connection
        connection.execute("DELETE FROM profiles WHERE id = %s", (profile["profile"]["id"],))


def _store(conn, profile, seed=42):
    times = timestamps(profile)
    return times, replace_run(
        conn,
        profile,
        seed,
        times,
        simulate(profile, seed).reported,
        context_states(profile, times),
        generate_schedule(profile, seed),
    )


def test_row_counts_match_sensors_times_samples(conn, profile):
    times, written = _store(conn, profile)
    profile_id = profile["profile"]["id"]
    assert written == 2 * len(times)
    assert count_rows(conn, "readings", profile_id) == 2 * len(times)
    assert count_rows(conn, "context_readings", profile_id) == len(times)
    assert count_rows(conn, "incident_labels", profile_id) == 8


def test_profile_without_context_stores_no_context_rows(conn, profile):
    del profile["context"]
    del profile["sensors"][0]["signal"]["state_offset"]
    _store(conn, profile)
    assert count_rows(conn, "context_readings", profile["profile"]["id"]) == 0


def test_second_run_replaces_the_first(conn, profile):
    times, _ = _store(conn, profile, seed=42)
    _store(conn, profile, seed=43)
    profile_id = profile["profile"]["id"]
    assert count_rows(conn, "readings", profile_id) == 2 * len(times)
    seed = conn.execute("SELECT seed FROM profiles WHERE id = %s", (profile_id,)).fetchone()[0]
    assert seed == 43


def test_stored_series_equals_the_reported_layer(conn, profile):
    profile["sensors"][0]["measurement_noise_std"] = 1.0
    times, _ = _store(conn, profile)
    stored_times, stored_values = read_series(
        conn, profile["profile"]["id"], "s1", times[-1]
    )
    result = simulate(profile, 42)
    assert stored_times == times[:-1]
    assert stored_values == result.reported["s1"].tolist()[:-1]
    assert stored_values != result.physical["s1"].tolist()[:-1]


def test_database_refuses_data_not_marked_simulated(conn, profile):
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        conn.execute(
            "INSERT INTO profiles (id, name, simulated, seed) VALUES (%s, %s, false, 0)",
            (profile["profile"]["id"], "not simulated"),
        )
