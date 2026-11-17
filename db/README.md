# db

All data is simulated. See ADR 0001 and 0002.

- `migrations/NNNN_<name>.sql`: numbered plain SQL files, one source of truth for the schema.
  - `0001`: the M1 schema.
  - `0002_runs`: drops the M1 data tables and creates `runs`, `run_splits` and the data tables,
    all keyed by `run_id` (`bigint` identity) with `ON DELETE CASCADE` from `runs`. It deletes
    stored simulated data; the data is regenerated from the seed.
  - `0003_state_ranges`: `sensor_state_ranges`, one row per run, sensor and state.
  - `0004_dq_results`: `dq_results`, one row per run and check (`passed`, `violations`,
    `checked_at`).
- Run ids are unique and stable but not consecutive: a rerun of the same run uses up an identity
  value. `runs.created_at` means "the last time the run's rows were written".
- `checks/<check_id>.sql`: the data-quality checks, run per `run_id` by
  `plantmon.core.quality.run_checks` and called by the demo, which exits non-zero when one fails.
  Each file is pure SQL with one query, the named parameter `%(run_id)s` and no schema prefix,
  and returns exactly one integer: the number of violations. Pipeline integrity only; plant
  behaviour is detector work.
  - `sample_count`: per sensor and split, the readings in `[start_ts, end_ts)` number
    `(end_ts - start_ts) / interval`; violations are the (sensor, split) pairs that differ. The
    gaps between splits are expected holes.
  - `regular_step`: within a sensor and a split, consecutive timestamps differ by exactly the
    interval; violations are the rows whose gap to the previous row is not.
  - `finite_values`: no NaN, `Infinity` or `-Infinity` in `readings.value`.
  - `outside_splits`: readings and context rows inside no split.
  - `labels_in_split`: every incident label lies inside the split it names.
  A rewrite of a run (`replace_run`) deletes its `dq_results`, so results are never stale.
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
