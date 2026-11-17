"""Write a simulated run to PostgreSQL and read series back."""

from datetime import datetime

import numpy as np
import psycopg

# shortcut: fixed local trust-auth database (ADR 0001, compose.yaml), make configurable for M7.
DSN = "postgresql://plantmon@127.0.0.1:5433/plantmon"


def connect() -> psycopg.Connection:
    # Without a timeout, an unreachable database blocked for about 130 s per attempt on Windows.
    return psycopg.connect(DSN, connect_timeout=5)


def replace_run(
    conn: psycopg.Connection,
    profile: dict,
    profile_sha256: str,
    seed: int,
    times: list[datetime],
    values: dict[str, np.ndarray],
    states: list[str] | None,
    incidents: list,
    splits: dict[str, tuple[datetime, datetime]],
) -> int:
    """Store one run in one transaction and return its run_id.

    The same profile id, seed and profile hash keeps its run_id and has its rows rewritten.
    Any other combination adds a run and leaves the others alone. splits maps a split name to its
    half-open (start, end) range.
    """
    meta = profile["profile"]
    with conn.transaction():
        run_id = conn.execute(
            "INSERT INTO runs (profile_id, name, simulated, seed, profile_sha256, interval_minutes)"
            " VALUES (%s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (profile_id, seed, profile_sha256) DO UPDATE SET created_at = now()"
            " RETURNING run_id",
            (
                meta["id"],
                meta["name"],
                meta["simulated"],
                seed,
                profile_sha256,
                profile["sampling"]["interval_minutes"],
            ),
        ).fetchone()[0]
        # Deleting sensors also deletes their readings and state ranges (ON DELETE CASCADE).
        # dq_results go too: results of the old rows must not survive a rewrite.
        for table in ("run_splits", "sensors", "context_readings", "incident_labels", "dq_results"):
            conn.execute(f"DELETE FROM {table} WHERE run_id = %s", (run_id,))
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO run_splits (run_id, split, start_ts, end_ts) VALUES (%s, %s, %s, %s)",
                [(run_id, name, *bounds) for name, bounds in splits.items()],
            )
            cur.executemany(
                "INSERT INTO sensors (run_id, id, asset, kind, unit, nominal_low, nominal_high)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    (run_id, s["id"], s["asset"], s["kind"], s["unit"], *s["nominal_range"])
                    for s in profile["sensors"]
                ],
            )
            if states is not None:
                cur.executemany(
                    "INSERT INTO sensor_state_ranges (run_id, sensor_id, state, low, high)"
                    " VALUES (%s, %s, %s, %s, %s)",
                    [
                        (
                            run_id,
                            s["id"],
                            state,
                            *s.get("nominal_range_by_state", {}).get(state, s["nominal_range"]),
                        )
                        for s in profile["sensors"]
                        for state in profile["context"]["states"]
                    ],
                )
            with cur.copy("COPY readings (run_id, sensor_id, ts, value) FROM STDIN") as copy:
                for sensor_id, series in values.items():
                    for ts, value in zip(times, series.tolist()):
                        copy.write_row((run_id, sensor_id, ts, value))
            if states is not None:
                with cur.copy("COPY context_readings (run_id, ts, state) FROM STDIN") as copy:
                    for ts, state in zip(times, states):
                        copy.write_row((run_id, ts, state))
            with cur.copy(
                "COPY incident_labels (run_id, start_ts, end_ts, class_id, incident_type, split)"
                " FROM STDIN"
            ) as copy:
                for i in incidents:
                    copy.write_row((run_id, i.start, i.end, i.class_id, i.incident_type, i.split))
    return run_id


def count_rows(conn: psycopg.Connection, table: str, run_id: int) -> int:
    # table comes from this codebase's own callers, never from user input.
    query = f"SELECT count(*) FROM {table} WHERE run_id = %s"
    return conn.execute(query, (run_id,)).fetchone()[0]


def read_series(
    conn: psycopg.Connection, run_id: int, sensor_id: str, until: datetime
) -> tuple[list[datetime], list[float]]:
    rows = conn.execute(
        "SELECT ts, value FROM readings WHERE run_id = %s AND sensor_id = %s AND ts < %s"
        " ORDER BY ts",
        (run_id, sensor_id, until),
    ).fetchall()
    return [r[0] for r in rows], [r[1] for r in rows]
