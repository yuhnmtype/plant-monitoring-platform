"""Write a simulated run to PostgreSQL and read series back."""

from datetime import datetime
from pathlib import Path

import numpy as np
import psycopg

# shortcut: fixed local trust-auth database (ADR 0001, compose.yaml), make configurable for M7.
DSN = "postgresql://plantmon@127.0.0.1:5433/plantmon"
SCHEMA_PATH = Path("db/schema.sql")


def connect() -> psycopg.Connection:
    # Without a timeout, an unreachable database blocked for about 130 s per attempt on Windows.
    return psycopg.connect(DSN, connect_timeout=5)


def apply_schema(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def replace_run(
    conn: psycopg.Connection,
    profile: dict,
    seed: int,
    times: list[datetime],
    values: dict[str, np.ndarray],
    states: list[str] | None,
    incidents: list,
) -> int:
    """Replace all stored data of this profile in one transaction. Return the readings written."""
    profile_id = profile["profile"]["id"]
    with conn.transaction():
        conn.execute("DELETE FROM profiles WHERE id = %s", (profile_id,))
        conn.execute(
            "INSERT INTO profiles (id, name, simulated, seed) VALUES (%s, %s, %s, %s)",
            (profile_id, profile["profile"]["name"], profile["profile"]["simulated"], seed),
        )
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO sensors (profile_id, id, asset, kind, unit, nominal_low, nominal_high)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    (profile_id, s["id"], s["asset"], s["kind"], s["unit"], *s["nominal_range"])
                    for s in profile["sensors"]
                ],
            )
            with cur.copy(
                "COPY readings (profile_id, sensor_id, ts, value) FROM STDIN"
            ) as copy:
                for sensor_id, series in values.items():
                    for ts, value in zip(times, series.tolist()):
                        copy.write_row((profile_id, sensor_id, ts, value))
            if states is not None:
                with cur.copy("COPY context_readings (profile_id, ts, state) FROM STDIN") as copy:
                    for ts, state in zip(times, states):
                        copy.write_row((profile_id, ts, state))
            with cur.copy(
                "COPY incident_labels"
                " (profile_id, start_ts, end_ts, class_id, incident_type, split) FROM STDIN"
            ) as copy:
                for i in incidents:
                    copy.write_row(
                        (profile_id, i.start, i.end, i.class_id, i.incident_type, i.split)
                    )
    return sum(len(series) for series in values.values())


def count_rows(conn: psycopg.Connection, table: str, profile_id: str) -> int:
    # table comes from this codebase's own callers, never from user input.
    query = f"SELECT count(*) FROM {table} WHERE profile_id = %s"
    return conn.execute(query, (profile_id,)).fetchone()[0]


def read_series(
    conn: psycopg.Connection, profile_id: str, sensor_id: str, until: datetime
) -> tuple[list[datetime], list[float]]:
    rows = conn.execute(
        "SELECT ts, value FROM readings WHERE profile_id = %s AND sensor_id = %s AND ts < %s"
        " ORDER BY ts",
        (profile_id, sensor_id, until),
    ).fetchall()
    return [r[0] for r in rows], [r[1] for r in rows]
