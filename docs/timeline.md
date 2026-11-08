# Timeline v2

Status: DRAFT. Written on 2026-11-07. Weekend milestones; the author works 1-4 hours per day. Hard stop: 31 January 2027.

## Dates

| Milestone | Dates | Scope |
|---|---|---|
| M0 | 6-8 Nov 2026 | Decisions, evaluation criteria (draft), repo skeleton, problem brief, timeline |
| M1 | 14-15 Nov | Simulator to database to one chart; tag `eval-criteria-v1` at the end |
| M2 | 21-22 Nov | Schema, indexes, data-quality checks, then profile 2 through the same pipeline |
| M3 | 28-29 Nov | Statistical detection and frozen evaluation on simulated data |
| Exams | 1-15 Dec | Project frozen: small commits at most, no milestone counted |
| Optional | 16-18 Dec | Weekdays after exams, extra time for M4 |
| M4 | 19-20 Dec and 26-27 Dec | ML method and public-benchmark evaluation, full size, two weekends |
| Optional | 28-31 Dec | Weekdays, extra time for M4 or M5 |
| M5 | 2-3 Jan 2027 | Dashboard, alerts, monthly KPI report |
| M6 | 9-10 Jan | Audit logging, detection rules, threat model |
| M7 | 16-17 Jan | Docker and CI |
| M8 | 23-24 Jan | Azure, demo, one-page summary, tag v1.0 |
| Buffer | 25-31 Jan | Hard stop on 31 Jan |

M4 keeps its full size and gets two weekends instead of being shrunk. The cost is that the buffer is one week, not two. The optional weekdays are there to protect it.

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
- Check that the proposed P2 incident counts and the sampling interval are feasible.
- Create the tag `eval-criteria-v1` after the author confirms the frozen values, before any detector runs on validation or test data.

If time:
- Seasonality in the simulator.

## M6 (9-10 Jan)

Carried over from M0:
- One-page threat-model outline, which grows into the short threat model.

The other M6 must and if-time items are written in its spec before the milestone starts.
