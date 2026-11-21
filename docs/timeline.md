# Timeline v2

Status: DRAFT. Written on 2026-11-07. Weekend milestones; the author works 1-4 hours per day. Hard stop: 31 January 2027.

## Dates

| Milestone | Dates | Scope |
|---|---|---|
| M0 | 6-8 Nov 2026 | Decisions, evaluation criteria (draft), repo skeleton, problem brief, timeline |
| M1 | 14-15 Nov | Simulator to database to one chart; tag `eval-criteria-v1` at the end |
| M2 | Part A from 15 Nov, Part B brought forward from 21-22 Nov (exam period from 1 Dec); M3 start unchanged unless Huy decides otherwise | Part A: migrations, runs, data-quality checks, indexes, tag `profile1-done`. Part B: profile 2 through the same pipeline, tag `profile2-done` |
| M3a | 28-29 Nov | Injection of the incident classes into profile 1, chart review, tag `m3-injection-frozen` |
| M3b | After the exams, in the 16-18 Dec slot (slip against the old row "M3, 28-29 Nov") | Evaluation code, detectors R0 and B1, validation sweep, one frozen test run on simulated data, tag `m3-done` |
| Exams | 1-15 Dec | Project frozen: small commits at most, no milestone counted |
| Optional | 16-18 Dec | Weekdays after exams: used by M3b (see the M3b row), so no longer extra time for M4 |
| M4 | 19-20 Dec and 26-27 Dec | ML method and public-benchmark evaluation, full size, two weekends |
| Optional | 28-31 Dec | Weekdays, extra time for M4 or M5 |
| M5 | 2-3 Jan 2027 | Dashboard, alerts, monthly KPI report |
| M6 | 9-10 Jan | Audit logging, detection rules, threat model |
| M7 | 16-17 Jan | Docker and CI |
| M8 | 23-24 Jan | Azure, demo, one-page summary, tag v1.0 |
| Buffer | 25-31 Jan | Hard stop on 31 Jan |

M4 keeps its full size and gets two weekends instead of being shrunk. The cost is that the buffer is one week, not two. The optional weekdays 28-31 Dec are there to protect it; the optional weekdays 16-18 Dec are now used by M3b.

## Rules

- New ideas go to `docs/backlog.md` first. Triage with three questions: which job-description gap it fills, how many hours it takes, what gets cut. Outcomes: replace something of equal size, use buffer time, or Future work.
- No new features after M6. After that: packaging, deployment, documentation, bug fixes.
- A milestone that slips shrinks the next one. Nothing is silently dropped.
- Each milestone has "must" and "if time" items, written in its own spec before the milestone starts.
- The README status table is updated after every milestone. CV bullets are written only for Done items.
- Evaluation criteria are never edited after the tag. Changes become a labelled v2 and v1 results stay.

## M0 (6-8 Nov)

Must:
- Six ADRs (done), draft evaluation criteria (done), repo skeleton (done), README status table (done), backlog (done).
- Problem brief and this timeline.

Moved, not dropped: the plant-profile YAML structure moves to the start of M1, and the threat-model outline moves to M6.

## M1 (14-15 Nov)

Must:
- Draft the plant-profile YAML structure first (moved from M0; structure only, no code).
- Seeded simulator, ingestion into PostgreSQL, one chart, one command. A minimal compose file starts only the database (ADR 0001).
- Regime or state information as a generic, optional context channel in the core (ADR 0006).
- Import smoke test in the project venv for every chosen library, then pin versions.
- Incident schedule with labels and a validator for P2; no injection into signals yet (moved to M3).
- Generic cross-sensor coupling (`follows`, linear) with a physical and a reported layer; profile 1 uses three relations.
- Real gap between splits and a separate daily phase per independent source.
- Check that the proposed P2 incident counts and the sampling interval are feasible.
- Create the tag `eval-criteria-v1` after the author confirms the frozen values, before any detector runs on validation or test data.

If time:
- Seasonality in the simulator.
- Inject drift, stuck sensor and replayed data.

## M2 (Part A from 15 Nov, Part B brought forward from 21-22 Nov; exam period from 1 Dec)

M1 finished on 11 Nov, before its planned weekend. M2 Part A starts on 15 Nov. M2 ends when Part B is done; it was planned to end on 22 Nov, and Part B is brought forward (exam period from 1 Dec). M3 start is unchanged unless Huy decides otherwise, so time gained is not assumed as M3 buffer.

Must, Part A (core work, ends with the tag `profile1-done`):
- Numbered SQL migrations with a small runner and `schema_migrations`; `db/schema.sql` is removed.
- A `runs` table, with every data table keyed by run.
- Optional per-state nominal range per sensor.
- Seed-42 regression: stored readings and schedule identical before and after Part A.
- Five data-quality checks for pipeline integrity, results in `dq_results`; the demo exits non-zero on a failure.
- Indexes kept only with measured `EXPLAIN (ANALYZE, BUFFERS)` before and after.
- Plant-term test driven by `plant_terms.txt` in each profile folder.
- The missing M1 test for "context.schedule.daily_hours must list every state".
- ADR 0007 for migrations, runs and data quality; a deviations log started with the profile 2 README line.

Must, Part B (brought forward from 21-22 Nov):
- Profile 2 confirmed on paper first, then `python -m plantmon demo --profile engine_test_cell` through the same pipeline.
- Tag `profile2-done` and a generality report with the raw `git diff profile1-done profile2-done -- src/plantmon db`.

If time:
- A separate `python -m plantmon dq --run <id>` command.
- Context row count check.

The full spec is `docs/specs/m2.md`. If Part A is not done by 21 Nov, that is a slip under the rules above and is reported; nothing is dropped silently.

## M3 (M3a 28-29 Nov, M3b after the exams)

M3 is split (decided 2026-11-20). M3a (28-29 Nov, before the exam period) is injection only. M3b (after the exams, in the 16-18 Dec slot) is the evaluation code, the detectors, the validation sweep and one frozen test run. This is a slip against the old plan "M3 = 28-29 Nov", not a gain: the optional time before M4 is used by M3b. M4 keeps 19-20 Dec and 26-27 Dec.

Carried over from M1:
- Inject the 7 incident classes into the signals, as the first must item of M3a (moved from M1; anything already injected as an M1 if-time item is not repeated).

The M3 must and if-time items are in `docs/specs/m3.md`.

## M6 (9-10 Jan)

Carried over from M0:
- One-page threat-model outline, which grows into the short threat model.

The other M6 must and if-time items are written in its spec before the milestone starts.
