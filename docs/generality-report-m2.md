# Generality report, M2 (profile 2)

Date: 2026-11-19. All data in this project is simulated. Profile 2 is a fictional engine test cell; no real engine data is used and no real test-cell experience is claimed. The criterion is defined in `docs/evaluation-criteria-v1.md` section 9 (frozen, not edited here).

Tags: `profile1-done` (2026-11-17, commit `0b00489`) and `profile2-done` (2026-11-19, commit `efac0da`, the same commit as `main` when this report was written).

## 1. Result

**Criterion met.** Adding profile 2 changed zero lines under the core paths `src/plantmon/` and `db/` between `profile1-done` and `profile2-done`. Raw output:

```
$ git diff profile1-done profile2-done -- src/plantmon db
(no output, exit 0)
```

The criterion is a line diff between the two tags. Section 3 lists the core capabilities that were added before `profile1-done` while profile 2 was already planned, and section 7 says what the result does not show.

## 2. What changed between the tags

Two commits lie between the tags (`git log --oneline profile1-done..profile2-done`):

```
efac0da M2 Part B: initial settings, evidence and schedule update
8f3e573 M2 Part B: engine_test_cell profile files (round 0)
```

Raw `git diff --stat profile1-done profile2-done`:

```
 docs/specs/m2.md                          |  60 ++++++++++++-
 docs/timeline.md                          |   8 +-
 profiles/engine_test_cell/README.md       |   9 +-
 profiles/engine_test_cell/plant_terms.txt |  14 +++
 profiles/engine_test_cell/profile.yaml    | 141 ++++++++++++++++++++++++++++++
 5 files changed, 225 insertions(+), 7 deletions(-)
```

By top-level folder (`git diff --name-only`, five files):

| Folder | Files | Which |
|---|---|---|
| `profiles/` | 3 | `engine_test_cell/profile.yaml` (new), `plant_terms.txt` (new), `README.md` (changed) |
| `docs/` | 2 | `specs/m2.md` (initial settings, tuning log, evidence), `timeline.md` (schedule wording) |
| `src/plantmon/`, `db/`, `tests/`, `scripts/`, repo root | 0 | |

## 3. Core capabilities added before `profile1-done`, while profile 2 was already known

These were added to the core before the tag, so the zero-change result above does not cover them. Profile 2 was already chosen as the engine test cell when they were designed (ADR 0006 is dated 2026-11-06). Commit hashes come from `git log`.

| Capability | Why it exists | Commits |
|---|---|---|
| Optional context channel (operating states, a daily schedule, an additive state offset in the simulator, a `context_readings` table) | ADR 0006: normal ranges in an engine cell depend on the operating regime, so regime information had to be a generic, optional channel from M1 on | ADR `4ca2438` (2026-11-07); implementation `47f52db` (M1, 2026-11-11: simulator, loader validation, `context_readings` in the M1 schema); test that `daily_hours` must list every state `19cd6f1` (2026-11-15) |
| Per-state nominal ranges: loader key `nominal_range_by_state`, migration `0003`, table `sensor_state_ranges`, one row per sensor and state of the profile (a left-out state uses the sensor's `nominal_range`) | Frozen criteria section 3 defines R0 as "outside range for the current regime if the profile defines regimes"; ADR 0006 names this consequence | decisions `196688d`; migration, table and store `adff3ed`; loader `bc0a163` (all 2026-11-17) |
| Migration runner and `schema_migrations` | ADR 0001 left the migration approach to M2 (ADR 0007) | runner `63d6243` (2026-11-15); `.gitattributes` `65fc4ad` |
| `runs` table, `run_id` on every data table, `run_splits` (migration `0002`) | Several runs in one database (seeds 42-46 and then profile 2) | `adff3ed` |
| Data-quality checks (`db/checks`, `dq_results`, migration `0004`, `plantmon.core.quality`, demo exit code) and ADR 0007 | Pipeline integrity checks | `12575d1`; ADR `0b00489` |

The runner, the runs table and the checks are generic and plant-agnostic (the plant-term test, commit `a3e5cb6`, checks this), but they were written before profile 2 existed as a file. The context channel and the per-state ranges were added because of profile 2 (ADR 0006).

**Consequence.** The zero-change result is measured from `profile1-done`. The additions in this section are the part a stricter reading of the criterion would count. This report lists them and does not argue them away.

## 4. The README fact

`profiles/engine_test_cell/README.md` existed since M0 (commit `4ca2438`, 2026-11-07), before `profile1-done`, while criteria section 9 says `profile1-done` is tagged before any profile 2 file is added. It had one line then. It is recorded in `docs/deviations.md` (dated 2026-11-17, before the tag, commit `0b00489`). It now has eight lines (commit `8f3e573`, 2026-11-19); that is a change inside the profile folder, not in the core.

## 5. What profile 2 exercised without a core change

- 5-minute sampling (profile 1 uses 15): 157,248 samples per sensor, 7 sensors, 1,100,736 readings per run.
- Three regimes (`idle`, `ramp`, `full_load`) through `context.states` and `daily_hours`, with an additive `state_offset` on two independent sensors.
- Chained `follows`: `vibration_rms` follows `shaft_speed`, which follows `throttle_command`.
- Per-state nominal ranges for six sensors. `intake_air_temp` has none, so it uses the fallback: 21 `sensor_state_ranges` rows for the run (7 sensors x 3 states), and the three rows of `intake_air_temp` are all equal to its `nominal_range`.
- The two renamed fault classes (`bearing_wear`, `oil_pressure_loss`) next to the five generic ids, with the same schedule rules.
- The parametrized tests picked up the new profile on their own: the profile validity and schedule tests, the demo test (clean run, five data-quality lines, exit code 0) and the plant-term test (`plant_terms.txt`, 14 terms). The suite went from 121 to 130 tests without any file under `tests/` changing.
- The demo (`python -m plantmon demo --profile engine_test_cell`) for seeds 42 and 43: exit code 0, all five data-quality checks passed, 1,100,736 readings per run.
- Held-out check of the per-state ranges (seeds 47-56): 0 of 9,434,880 readings outside their state range for the six sensors with state ranges, and 0 of 1,572,480 for `intake_air_temp`.

Source for the numbers: `docs/specs/m2.md`, section "Part B initial settings", subsection "Evidence".

## 6. Limits and negative results

- **Overlapping ranges.** The `ramp` and `full_load` ranges overlap on `vibration_rms` ([5.2, 5.5]), on `oil_pressure` ([4.0, 4.05], a rounding effect of 0.05 bar) and on `coolant_outlet_temp` ([82.5, 86.0], the widest). In an overlap a reading is in range for both states, so a per-state range alone does not tell `ramp` from `full_load` there.
- **One contiguous span per state.** The regimes follow a fixed daily clock, so the day ends with a step from `full_load` to `idle` at midnight, and `ramp` is a step, not a gradual change.
- **Chart.** The demo chart draws only the global `nominal_range` (the hull of the state ranges), not the per-state ranges, and its legend overlaps the last days of the line. This was observed on the demo chart. It is core code and was not changed.
- **Alarm merge window.** The frozen criteria use "G = 3 sampling intervals". That is 15 minutes on this profile and 45 minutes on profile 1.
- **Index measurement.** The Part A index measurement (314,496 readings per run, ADR 0007) was not repeated at 1,100,736 readings per run, and its result is not claimed for profile 2.
- **Reproducibility across machines.** For profile 1, the readings hash differs between Windows and Linux (the first reading is identical; the cause is unknown). The derived per-state ranges of profile 2 matched on both. So "same seed, identical readings" is a claim for one machine and one set of library versions (`docs/specs/m2.md`, Known limits).
- **Context rows are not counted.** No data-quality check counts `context_readings` rows: the Part A "if time" item (a context row count check) was not done and is in `docs/backlog.md` as Future work. `outside_splits` only finds context rows that lie outside every split. For profile 2 the demo stored 157,248 context rows, equal to the samples per sensor, but no check confirms it.
- **Time.** The demo took 16.2 s (seed 42) and 12.9 s (seed 43) on profile 2, against about 4 s on profile 1. The full test run took 25.4 s for 130 tests (23.4 s on a second run), against about 10 s for 121. These are observations on one machine; no performance claim is made.

## 7. What this does not show

- No real engine data, no real test cell, and no real users: everything is simulated.
- No detection results on profile 2. Detection evaluation on it is optional (criteria section 9) and was not done.
- The criterion is a line diff between two tags. It does not prove that a third profile would also need no core change.
- It does not count the capabilities in section 3, which were added earlier.

## 8. Tuning

0 of 2 tuning rounds were used. The profile was frozen at `profile2-done` (the tuning log in `docs/specs/m2.md` has only "Round 0, 2026-11-18: initial settings"). Any change after the tag is a labelled v2.

## 9. Reproduce

From the repo root in Windows PowerShell, with Docker running and the project venv installed (`python -m venv .venv`, then `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`):

```
.\.venv\Scripts\python.exe -m plantmon demo --profile water_treatment
.\.venv\Scripts\python.exe -m plantmon demo --profile engine_test_cell
.\.venv\Scripts\python.exe -m plantmon demo --profile engine_test_cell --seed 43
git diff profile1-done profile2-done -- src/plantmon db
git diff --stat profile1-done profile2-done
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

The `git diff -- src/plantmon db` command must print nothing.
