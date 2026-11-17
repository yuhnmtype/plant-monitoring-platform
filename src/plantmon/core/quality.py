"""Run the data-quality checks under db/checks and store their results in dq_results."""

from dataclasses import dataclass
from pathlib import Path

import psycopg

CHECKS_DIR = Path("db/checks")


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    passed: bool
    violations: int


def run_checks(
    conn: psycopg.Connection, run_id: int, directory: Path = CHECKS_DIR
) -> list[CheckResult]:
    """Run every *.sql file in sorted order for one run and upsert each result.

    A check file holds one query with the parameter %(run_id)s that returns one integer, the
    number of violations. The check id is the file name without .sql. Fails closed: a missing or
    empty directory raises instead of returning no results, so no check can be skipped silently.
    """
    paths = sorted(directory.glob("*.sql"))
    if not paths:
        raise ValueError(f"check directory {directory} does not exist or holds no *.sql file")
    results = []
    with conn.transaction():
        for path in paths:
            rows = conn.execute(path.read_text(encoding="utf-8"), {"run_id": run_id}).fetchall()
            if len(rows) != 1 or len(rows[0]) != 1 or not isinstance(rows[0][0], int):
                raise ValueError(f"check {path.name} must return exactly one integer")
            result = CheckResult(path.stem, rows[0][0] == 0, rows[0][0])
            conn.execute(
                "INSERT INTO dq_results (run_id, check_id, passed, violations)"
                " VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (run_id, check_id)"
                " DO UPDATE SET passed = EXCLUDED.passed, violations = EXCLUDED.violations,"
                " checked_at = now()",
                (run_id, result.check_id, result.passed, result.violations),
            )
            results.append(result)
    return results
