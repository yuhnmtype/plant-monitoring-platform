# Engine test cell (profile 2)

A fictional, simulated engine test cell, added at the end of M2 as the generality test (ADR 0006). All data is simulated. No real engine data is used, and no real test-cell experience is involved: every number is invented for the simulation.

- Three operating regimes on a fixed daily clock (UTC): `idle` 0-9 h, `ramp` 9-11 h, `full_load` 11-24 h.
- Seven sensors: `throttle_command`, `shaft_speed`, `vibration_rms`, `exhaust_gas_temp`, `oil_pressure`, `coolant_outlet_temp`, `intake_air_temp`.
- Sampling interval: 5 minutes.
- Run it with `python -m plantmon demo --profile engine_test_cell`.
