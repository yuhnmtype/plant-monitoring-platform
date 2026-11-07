# ADR 0006: Profile 2 is a simulated engine test cell

- Status: Accepted
- Date: 2026-11-06

## Context
Profile 2 is the generality test. The more its signals differ from the water profile, the more the test proves.

## Decision
Profile 2 is a small engine test cell, simulated only: temperatures, pressures, vibration and rotational speed, with operating regimes (idle, ramp, full load). No real engine data is used and no claim of real aerospace or test-cell experience is made.

Frozen success criterion: adding profile 2 requires zero changes to core code. "Core" means the paths listed in the evaluation criteria, section 9. If core changes anyway, each change is recorded with its reason in a generality report, and the criterion is reported as not met.

## Alternatives considered
- Solar plus battery microgrid: strong seasonality, but closer to the water profile in signal type.
- EV charging network: event-based data, the most likely to force core changes, so the highest timeline risk.
- Cold chain: mostly a temperature threshold, so a weak test.

## Consequences
- Normal ranges in an engine cell depend on the operating regime, while water is close to steady state. A core that assumes one fixed normal range per sensor would fail the criterion by design.
- So regime or state information must be a generic, optional context channel in the core from M1 on. This changes the M1 design; confirmed by Huy on 2026-11-06.
