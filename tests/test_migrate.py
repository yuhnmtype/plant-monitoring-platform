"""Migration runner tests in a throwaway schema. Skipped, visibly, when the database is down."""

import pytest

from plantmon.core.migrate import MIGRATIONS_DIR, MigrationError, migrate


def _state(conn):
    """Every column of every table in the schema, plus the schema_migrations rows if any."""
    columns = conn.execute(
        "SELECT table_name, column_name, data_type FROM information_schema.columns"
        " WHERE table_schema = current_schema() ORDER BY 1, 2"
    ).fetchall()
    applied = None
    if any(column[0] == "schema_migrations" for column in columns):
        applied = conn.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall()
    return columns, applied


def test_empty_schema_applies_every_migration(db):
    versions = [path.name.split("_")[0] for path in sorted(MIGRATIONS_DIR.glob("*.sql"))]
    assert versions and versions[0] == "0001"
    assert migrate(db) == versions
    columns, applied = _state(db)
    assert [row[0] for row in applied] == versions
    assert "readings" in {column[0] for column in columns}


def test_second_run_applies_nothing_and_changes_nothing(db):
    migrate(db)
    before = _state(db)
    assert migrate(db) == []
    assert _state(db) == before


def test_changed_checksum_of_an_applied_file_is_refused(db, tmp_path):
    first = tmp_path / "0001_one.sql"
    first.write_bytes(b"CREATE TABLE one (id integer);\n")
    assert migrate(db, tmp_path) == ["0001"]
    before = _state(db)

    first.write_bytes(b"CREATE TABLE one (id bigint);\n")
    (tmp_path / "0002_two.sql").write_bytes(b"CREATE TABLE two (id integer);\n")
    with pytest.raises(MigrationError, match="migration 0001 was applied with checksum"):
        migrate(db, tmp_path)
    assert _state(db) == before


def test_tables_without_schema_migrations_are_refused(db):
    db.execute("CREATE TABLE stray (id integer)")
    before = _state(db)
    with pytest.raises(MigrationError, match=r"has tables \(stray\) but no schema_migrations"):
        migrate(db)
    assert _state(db) == before


def test_two_files_with_the_same_version_are_refused(db, tmp_path):
    (tmp_path / "0001_one.sql").write_bytes(b"CREATE TABLE one (id integer);\n")
    (tmp_path / "0001_two.sql").write_bytes(b"CREATE TABLE two (id integer);\n")
    before = _state(db)
    with pytest.raises(MigrationError, match="share a version number"):
        migrate(db, tmp_path)
    assert _state(db) == before


def test_missing_file_of_an_applied_migration_is_refused(db, tmp_path):
    first = tmp_path / "0001_one.sql"
    first.write_bytes(b"CREATE TABLE one (id integer);\n")
    migrate(db, tmp_path)
    before = _state(db)

    first.unlink()
    (tmp_path / "0002_two.sql").write_bytes(b"CREATE TABLE two (id integer);\n")
    with pytest.raises(MigrationError, match="migration 0001 was applied .* now has no file"):
        migrate(db, tmp_path)
    assert _state(db) == before
