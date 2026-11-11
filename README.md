# plant-monitoring-platform

A generic monitoring platform for industrial plants, built and evaluated entirely on simulated data. It aims to store sensor readings without any plant-specific code in the core, detect incidents and compare detectors against baselines under evaluation criteria fixed in advance, and record who accessed or changed what in an audit log. Plants are added as profiles: a water treatment plant first, then an engine test cell as the test of whether the core is really generic. This is a portfolio project and claims no real industrial (OT) experience.

**All data is simulated.**

## Status

| Milestone | Scope | Status |
|---|---|---|
| M0 | Decisions, evaluation criteria, repo skeleton | Done |
| M1 | Seeded simulator (simulated data), incident schedule with validator, PostgreSQL store, one-command demo; evaluation criteria frozen by the tag `eval-criteria-v1` | Done |
| M2 | Schema, indexes, data-quality checks, profile 2 | Not started |
| M3 | Statistical detection and frozen evaluation | Not started |
| M4 | ML method and public-benchmark evaluation | Not started |
| M5 | Dashboard, alerts, monthly KPI report | Not started |
| M6 | Audit logging, detection rules, threat model | Not started |
| M7 | Docker and CI | Not started |
| M8 | Azure, demo, one-page summary, tag v1.0 | Not started |

Allowed values: Not started / In progress / Done. CV bullets are written only for Done items.

## How to run

Needs Python 3.15 and a running Docker. In Windows PowerShell, from the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m plantmon demo --profile water_treatment
```

This starts a local PostgreSQL container, stores one simulated run and writes `data/generated/chart.png`. Stop the database with `docker compose down`.

## Results

TBD

## Known limitations

TBD
