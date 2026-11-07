# ADR 0005: Thin FastAPI layer as the audit point

- Status: Accepted
- Date: 2026-11-06

## Context
The platform must record who accessed or changed what, for four roles (operator, maintenance engineer, manager, admin).

## Decision
Put a thin FastAPI service between the database and the dashboard. Every request is authenticated as a simulated user, checked against the role, and written to the audit log. Failed logins and configuration changes are logged there too.

## Alternatives considered
- Audit inside the dashboard: less code, but it couples audit records to the UI framework and leaves no clean boundary to test.

## Consequences
- One more service and more tests.
- Authentication is deliberately simple. Demo users are created at seed time with generated throwaway passwords; no real credentials or secrets are committed. The threat model states that this is a simulation and not production-grade authentication.
- The 3-5 detection rules of M6 read the audit log produced here.
