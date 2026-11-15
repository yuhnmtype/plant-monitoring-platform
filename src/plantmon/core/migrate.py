"""Apply the numbered SQL files under db/migrations, once each and in order."""

import hashlib
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path("db/migrations")


class MigrationError(RuntimeError):
    """The runner refused. Nothing was changed."""


def migrate(conn: psycopg.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations in the first schema of the search_path. Return their versions.

    Call it on a connection with no open transaction: each file and its schema_migrations row
    are then committed together. Inside an open transaction they are only savepoints.
    """
    files = {path.name.split("_")[0]: path.read_bytes() for path in sorted(directory.glob("*.sql"))}
    if len(files) != len(list(directory.glob("*.sql"))):
        raise MigrationError(f"two files in {directory} share a version number")
    checksums = {version: hashlib.sha256(raw).hexdigest() for version, raw in files.items()}

    with conn.transaction():
        schema = conn.execute("SELECT current_schema()").fetchone()[0]
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()"
                " ORDER BY tablename"
            )
        ]
        if tables and "schema_migrations" not in tables:
            raise MigrationError(
                f"schema {schema!r} has tables ({', '.join(tables)}) but no schema_migrations"
                " table, so it was not created by this runner. Nothing was changed."
            )
        applied = {}
        if tables:
            applied = dict(conn.execute("SELECT version, checksum FROM schema_migrations"))
        for version, checksum in sorted(applied.items()):
            if checksums.get(version) != checksum:
                raise MigrationError(
                    f"migration {version} was applied with checksum {checksum}, but its file in"
                    f" {directory} now has {checksums.get(version, 'no file')}. An applied"
                    " migration must not change. Nothing was changed."
                )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations"
            " (version text PRIMARY KEY, checksum text NOT NULL)"
        )

    pending = [version for version in files if version not in applied]
    for version in pending:
        with conn.transaction():
            conn.execute(files[version])
            conn.execute(
                "INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)",
                (version, checksums[version]),
            )
    return pending
