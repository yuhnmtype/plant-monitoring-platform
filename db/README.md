# db

All data is simulated. See ADR 0001 and 0002.

- `migrations/NNNN_<name>.sql`: numbered plain SQL files, one source of truth for the schema.
  - `0001`: the M1 schema.
  - `0002_runs`: drops the M1 data tables and creates `runs`, `run_splits` and the data tables,
    all keyed by `run_id` (`bigint` identity) with `ON DELETE CASCADE` from `runs`. It deletes
    stored simulated data; the data is regenerated from the seed.
  - `0003_state_ranges`: `sensor_state_ranges`, one row per run, sensor and state.
- Runs: `UNIQUE (profile_id, seed, profile_sha256)`. The same profile, seed and profile hash keeps
  its `run_id` and has its rows rewritten in one transaction; another seed or another hash adds a
  run. `profile_sha256` is the SHA-256 of the raw bytes of the profile file.
- `run_splits.end_ts` is exclusive: a split holds `start_ts <= ts < end_ts`.
- `sensor_state_ranges` is filled only for a profile with states: every state of the profile, the
  sensor's declared range for it or else the sensor's `nominal_range`. No fallback logic is needed
  in a consumer.
- The runner is `plantmon.core.migrate.migrate(conn)`; the demo calls it. It applies pending
  files in order, each file and its `schema_migrations` row (version, SHA-256 of the raw file
  bytes) in one transaction, inside the first schema of the connection's `search_path`.
- The runner refuses, and changes nothing, when
  - an applied file's checksum has changed or the file is gone: never edit an applied
    migration, add a new one;
  - two files share a version number;
  - the schema has tables but no `schema_migrations` (a database created before the runner).
- `.gitattributes` keeps `*.sql` at LF on every checkout, so checksums are the same everywhere.
