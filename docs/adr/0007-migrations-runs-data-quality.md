# ADR 0007: Migrations, runs and data quality as SQL

- Status: Accepted
- Date: 2026-11-17

## Context
ADR 0001 defers the migration approach to M2. ADR 0002 describes data quality as "constraints plus a checker that reads the metadata tables". M2 needs several simulated runs (seeds 42-46, then profile 2) in one database, a way to change the schema without losing track of what was applied, and checks that the stored data is what the pipeline meant to write. All data is simulated.

The decisions below were confirmed by Huy on 2026-11-14 and 2026-11-15 (`docs/specs/m2.md`).

## Decision
**Migrations.** Numbered plain SQL files `db/migrations/NNNN_<name>.sql`, applied by a small runner in core (`plantmon.core.migrate`). No migration library.
- The runner applies pending files in order. Each file and its `schema_migrations` row (version and SHA-256 of the raw file bytes) are written in one transaction.
- It refuses, names the problem and changes nothing when an applied file's checksum has changed or the file is gone, when two files share a version, or when tables exist but `schema_migrations` does not.
- `.gitattributes` sets `eol=lf` for `*.sql` and `*.yaml`, so checksums and the profile hash are the same on every checkout.
- `0001` is the M1 schema, byte for byte. `0002` introduces runs and drops the M1 data tables: their content is simulated and is regenerated from the seed. `0003` and `0004` add the per-state range table and `dq_results`. An applied file is never edited; a change is a new file.
- `db/schema.sql` is removed, so the migration files are the one source of truth.

**Runs.** `runs` has a `bigint` identity `run_id`, the profile id and name, `simulated` (CHECK), seed, SHA-256 of the raw profile file, sampling interval and `created_at`. Every data table is keyed by `run_id` with `ON DELETE CASCADE` from `runs`. `run_splits` stores the split bounds of each run (end exclusive).
- `UNIQUE (profile_id, seed, profile_sha256)`: the same profile, seed and profile hash keeps its `run_id` and has its rows deleted and rewritten in one transaction. Another seed, or the same seed with a changed profile file, adds a run.
- Run ids are unique and stable but not consecutive: a rerun uses up an identity value. `created_at` means the last time the run's rows were written.

**Data quality.** Five SQL files under `db/checks/`: sample count, regular step, finite values, nothing outside the splits, labels inside their split. Each file holds one query with the named parameter `%(run_id)s` and returns one integer, the number of violations.
- Core code (`plantmon.core.quality`) runs every file for one run and upserts the result into `dq_results` (run, check id, passed, violation count, `checked_at`). It raises when the check directory is missing or empty, so a check cannot be skipped silently. Rewriting a run deletes its results.
- The demo prints one line per check and exits non-zero when one fails.
- The checks cover pipeline integrity only. Plant behaviour (stuck values, physical limits, outliers) is detector work, not data quality.
- No new constraints are added for data quality. Some checks compare many rows (counts per split, consecutive timestamps), which a row constraint does not express.

**Indexes.** None added in Part A; see Consequences.

## Alternatives considered
- A migration library: not used. The need is ordered apply, a checksum and a refusal, which the runner does in about 60 lines.
- Database constraints or triggers as the checker (ADR 0002's wording): not used for the five checks, see above.
- Keeping one stored run per profile (the M1 behaviour): rejected, because seeds 42-46 and profile 2 must coexist and be compared.

## Consequences
- Relation to ADR 0001: this ADR answers its open question (plain SQL files, no tool). PostgreSQL in Docker is unchanged.
- Relation to ADR 0002: the tables stay generic and plant-agnostic. Its "constraints plus a checker" becomes "a checker of SQL files and results in `dq_results`", with the existing CHECK constraints unchanged.
- The runner and the checks are core code written before profile 2 exists as a file; this is listed in the generality report (Part B).
- The migration runner has no lock against two processes running at once. It is a local single-user tool at this stage.
- "Same seed, identical readings" holds on one machine and one set of library versions (`docs/specs/m2.md`, Known limits).

### Index result (negative; measured 2026-11-17, simulated data)
No index was added. The decision rule was fixed before measuring: add an index only when the plan changes (the sequential scan is gone, or shared buffers read drop clearly) and the median execution time of three runs is at least 2x faster.

Setup: PostgreSQL 18.6 in Docker (`127.0.0.1:5433`), five runs (run ids 1, 3, 6, 7, 8; seeds 42-46), 1,572,480 readings (5 x 314,496), `ANALYZE readings` run. Query, with a 14-day window at the start of run 6 as in the demo chart:

```sql
SELECT sensor_id, ts, value FROM readings
WHERE run_id = 6 AND ts >= '2025-01-01 00:00:00+00' AND ts < '2025-01-15 00:00:00+00';
```

The query returns 8,064 rows. The primary key `(run_id, sensor_id, ts)` already serves it: the plan is a Bitmap Index Scan on `readings_pkey` with 7 index searches (probably one per sensor plus one, a PostgreSQL 18 behaviour that was inferred from the plan, not stated by it) and 72 heap blocks, with no sequential scan. The candidate `CREATE INDEX ... ON readings (run_id, ts)` was measured inside a transaction that was rolled back, so nothing was kept.

| Measure (three runs in a row) | Primary key only | Candidate `(run_id, ts)` |
|---|---|---|
| Execution time, ms (run 1, 2, 3) | 1.090, 1.215, 0.771 | 1.029, 0.781, 0.902 |
| Median execution time, ms | 1.090 | 0.902 |
| Shared buffers, run 1 | hit 167, read 7 | hit 75, read 16 |
| Shared buffers, runs 2 and 3 (warm) | hit 163 | hit 88 |
| Index searches | 7 | 1 |
| Plan shape | Bitmap Index Scan, Bitmap Heap Scan | the same |
| Extra index size | none | 19 MB (primary key: 115 MB) |

The median is 1.2x faster, below the 2x the rule needs, and the ranges of the warm runs overlap. The candidate lowers the buffers read from the index, but the heap blocks are the same. So the rule says no, and no migration `0005` exists. The raw `EXPLAIN (ANALYZE, BUFFERS)` plans of all six runs are in `docs/specs/m2.md`.

Limits: sub-millisecond times on one machine, three runs, one window at the start of a run. No claim is made about other windows, other queries or other data sizes. The 7 index searches suggest the primary key is used with PostgreSQL 18's skip scan (inferred, not measured). The result was measured on PostgreSQL 18.6 only; on an older major version the primary key alone may serve a window across sensors less efficiently, so re-measure if the Postgres major version changes (for example in CI).
