"""SHA-256 of the stored readings and incident schedule (docs/specs/m2.md, Part A item 4).

All data is simulated. Run from the repo root:
    python scripts/regression_hash.py --filter-column profile_id --filter-value water_treatment

Each row becomes one UTF-8 line ending in "\\n". Timestamps are converted to UTC explicitly,
so the result does not depend on the session or machine time zone.
"""

import argparse
import hashlib
from datetime import UTC

from psycopg import sql

from plantmon.core.store import connect

READINGS = (
    "SELECT sensor_id, ts, value FROM readings WHERE {} = %s"
    ' ORDER BY sensor_id COLLATE "C", ts'
)
LABELS = (
    "SELECT class_id, incident_type, split, start_ts, end_ts FROM incident_labels"
    " WHERE {} = %s ORDER BY start_ts"
)


def _utc(ts) -> str:
    return ts.astimezone(UTC).isoformat()


def _hash(conn, query: str, column: str, value: str, line) -> tuple[str, int]:
    digest, rows = hashlib.sha256(), 0
    with conn.cursor() as cur:
        for row in cur.stream(sql.SQL(query).format(sql.Identifier(column)), (value,)):
            digest.update((line(row) + "\n").encode("utf-8"))
            rows += 1
    return digest.hexdigest(), rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--filter-column", required=True)
    parser.add_argument("--filter-value", required=True)
    args = parser.parse_args()
    with connect() as conn:
        readings = _hash(
            conn, READINGS, args.filter_column, args.filter_value,
            lambda r: f"{r[0]},{_utc(r[1])},{r[2]!r}",
        )
        labels = _hash(
            conn, LABELS, args.filter_column, args.filter_value,
            lambda r: f"{r[0]},{r[1]},{r[2]},{_utc(r[3])},{_utc(r[4])}",
        )
    print(f"readings        rows={readings[1]} sha256={readings[0]}")
    print(f"incident_labels rows={labels[1]} sha256={labels[0]}")


if __name__ == "__main__":
    main()
