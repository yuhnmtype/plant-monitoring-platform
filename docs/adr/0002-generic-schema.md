# ADR 0002: Generic readings table plus metadata tables

- Status: Accepted
- Date: 2026-11-06

## Context
The core must know nothing about water. Adding profile 2 must need zero core changes (see ADR 0006).

## Decision
One long-format readings table (sensor id, timestamp, value) plus metadata tables. Everything plant-specific is rows and YAML, never columns or tables.

## Alternatives considered
- One table per sensor type: simpler per-type queries, but every new profile would change the schema, which breaks the frozen generality criterion.

## Consequences
- Wide views for plotting need pivoting. Mitigation: a composite index on (sensor id, timestamp) and views; no performance claim is made before it is measured.
- Data-quality checks (M2) are expressed as constraints plus a checker that reads the metadata tables.

## Design notes (proposal, not confirmed)
- Ground-truth incident labels live in their own table that detectors never read.
- Tables expected: plants/profiles, assets, sensors (unit, kind, nominal range), readings, incident labels, alerts, audit log.
- Operating-regime information (needed by profile 2) is handled by the optional context channel in ADR 0006.
