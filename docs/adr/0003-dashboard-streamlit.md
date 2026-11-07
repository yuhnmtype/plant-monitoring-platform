# ADR 0003: Streamlit dashboard

- Status: Accepted
- Date: 2026-11-06

## Context
The dashboard needs trends, alerts and a monthly KPI report, and it must run in Docker and CI like the rest of the code.

## Decision
Build the dashboard in Streamlit. It reads data only through the API layer (ADR 0005).

## Alternatives considered
- Power BI: a common reporting tool, but a .pbix file is not practical to test in CI or to ship in `docker compose up`.
- Both: covers both skills but costs hours that the timeline does not have.

## Consequences
- No Power BI claim on the CV.
- Possible backlog item (not promised): a read-only database view that Power BI could connect to. It goes through the triage in the brief before any work starts.
- Azure hosting of a Streamlit container is not verified yet; it is the M8 timebox.
