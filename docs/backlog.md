# Backlog

Triage questions for every new idea:

1. Which job-description gap does it fill?
2. How many hours does it take?
3. What gets cut to make room?

| Idea | Gap | Hours | What gets cut | Outcome (replace / buffer / Future work) |
|---|---|---|---|---|
| `follows`: lag | None named; simulator realism only | About 2 (estimate) | Nothing while it stays in Future work | Future work |
| `follows`: integrator relation (tank level = integral of inflow minus outflow) | None named; simulator realism only | About 4 (estimate) | Nothing while it stays in Future work | Future work |
| Regime-dependent gain or noise (relations and noise level that change with the context state) | None named; simulator realism only | About 4 (estimate) | Nothing while it stays in Future work | Future work |
| Context schedules other than `daily_hours` (test cycles not tied to the clock) | None named; simulator realism only | About 5 (estimate) | Nothing while it stays in Future work | Future work |
| Behaviour checks in data quality (stuck value, physical limits) | None named; this is detector work under the M2 decision, not pipeline integrity | About 3 (estimate) | Nothing while it stays in Future work | Future work |
| A separate `python -m plantmon dq --run <id>` command | None named; convenience | Not estimated | Nothing while it stays in Future work | Future work |
| Context row count check (when a profile has states, context rows equal the kept timestamps) | None named; pipeline integrity | Not estimated | Nothing while it stays in Future work | Future work |
| Injection targets for profile 2, as a labelled v2 of the profile (profile 2 is frozen at `profile2-done`) | Tests that the injection code is generic; M3 does not test it (`docs/specs/m3.md`, Q5) | Not estimated | Nothing while it stays in Future work | Future work |
| Relation-residual detector B2: scores the deviation from the profile's `follows` relations | Relation-based classes that a per-sensor baseline can miss (weak pump, valve fault, manipulated readings) | Not estimated | Nothing while it stays in Future work | Future work |

Free-form formulas in `follows` are not planned.
