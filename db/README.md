# db

All data is simulated. See ADR 0001 and 0002.

- `migrations/NNNN_<name>.sql`: numbered plain SQL files. `0001` is the M1 schema.
- The runner is `plantmon.core.migrate.migrate(conn)`; the demo calls it. It applies pending
  files in order, each file and its `schema_migrations` row (version, SHA-256 of the raw file
  bytes) in one transaction, inside the first schema of the connection's `search_path`.
- The runner refuses, and changes nothing, when
  - an applied file's checksum has changed or the file is gone: never edit an applied
    migration, add a new one;
  - the schema has tables but no `schema_migrations` (a database created before the runner).
- `.gitattributes` keeps `*.sql` at LF on every checkout, so checksums are the same everywhere.
