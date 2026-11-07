# ADR 0001: PostgreSQL in Docker

- Status: Accepted
- Date: 2026-11-06

## Context
The platform stores simulated readings, metadata, labels, alerts and audit records. It must start with one command from a clean clone. Project 1 already shows SQLite; this project should show a server-side relational database.

## Decision
Use PostgreSQL, run in Docker.

## Alternatives considered
- SQLite: no setup, but a single-file database with no role model to support the audit story, and it duplicates what project 1 already shows.

## Consequences
- M1 needs a minimal compose file that starts only the database. Containerising the full app stays in M7.
- CI needs a Postgres service container.
- A migration approach (plain SQL files or a migration tool) is decided in M2.
- Database extensions for time series are out of scope for v1.
