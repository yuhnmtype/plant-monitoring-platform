# ADR 0004: Simulator first, BATADAL as a secondary benchmark

- Status: Accepted
- Date: 2026-11-06

## Context
Self-generated data lets the author control both the anomaly and the detector, so a public benchmark adds credibility. The brief required checking availability and licence first.

## Decision
- Primary evaluation: the simulator, which labels both physical faults and attacks.
- Secondary evaluation: BATADAL, verified on 2026-11-06 (see `docs/benchmarks/batadal-check.md`).
- BATADAL files are never committed. A script downloads them from the official URLs into a git-ignored folder, and the paper is cited.

## Alternatives considered
- Simulator only, with limits stated: safest for time, weaker evidence.

## Consequences
- The data page carries both "all rights reserved" and a CC BY 4.0 statement, so redistribution is not assumed.
- BATADAL has an attack flag only, so it tests attack detection, not fault-versus-attack separation.
- BATADAL results are reported separately and never pooled with simulator results.
- If a trustworthy label source for the BATADAL test set cannot be established, that part is dropped and the README says so.
