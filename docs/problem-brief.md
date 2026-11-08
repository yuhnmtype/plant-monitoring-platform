# Problem brief

Status: DRAFT for M0. All data in this project is simulated. No real plant, real credentials or real industrial (OT) experience is claimed.

## 1. Problem

An unusual sensor reading can have different causes. A device may be failing (a physical fault), or the data or commands may have been manipulated (tampering). The right response differs: maintenance for a fault, a security review for tampering. Operators also need a record of who accessed or changed what.

This project builds a platform that ingests simulated plant data, detects anomalous periods, tries to tell physical faults from tampering, and keeps an audit trail. Everything plant-specific lives in a plant profile, so the core stays generic.

## 2. Scene

- Profile 1: a fictional water-treatment plant.
- Profile 2: a small simulated engine test cell, added at the end of M2 as a generality test (ADR 0006).

## 3. Users (simulated personas, assumed needs)

| Role | Assumed need |
|---|---|
| Operator | See current trends and open alerts |
| Maintenance engineer | See which asset and sensor an alert points to and whether it looks like a fault |
| Manager | Read a monthly KPI report |
| Admin | Review the audit log and configuration changes |

These needs are design assumptions, not findings from real users.

## 4. Incident classes (profile 1)

The simulator only produces anomalous signal patterns. It contains no exploit code and no attack instructions.

| Class | Type | Pattern in the simulated data |
|---|---|---|
| Sensor drift | Physical fault | One sensor slowly moves away from its true value |
| Stuck sensor | Physical fault | One sensor keeps reporting the same value |
| Weak pump | Physical fault | Flow or pressure falls short of what the pump command implies |
| Valve fault | Physical fault | Valve position and downstream flow disagree |
| Manipulated readings | Attack | Reported values are altered and no longer agree with related sensors |
| Manipulated commands | Attack | Actuator commands change outside the normal operating pattern |
| Replayed data | Attack | An earlier stretch of readings is repeated |

## 5. In scope

Seeded simulator with labelled incidents; relational database with data-quality checks; statistical baseline and one ML method evaluated under frozen criteria; dashboard with trends, alerts and a monthly KPI report; thin API layer with audit logging, 3-5 detection rules and a short threat model; Docker, tests and CI; Azure deployment only if the free tier allows and a working URL exists.

## 6. Out of scope

- Real plant data and any claim of real industrial experience.
- A profile-creation UI and a plugin framework.
- Production-grade authentication.
- New features after M6 (only packaging, deployment, documentation and bug fixes).

## 7. Success criteria

- Evaluation follows `docs/evaluation-criteria-v1.md`, including negative results.
- Profile 2 is added with zero changes to core code, or every change is recorded with its reason.
- `docker compose up` works from a clean clone and CI is green.
- Every README claim has a working demo or a result behind it.

## 8. Known limitations

- Simulated data cannot show real-world performance.
- The simulator and the detectors are written by the same person.
- One public benchmark (BATADAL) has attack labels only, so it cannot test fault-versus-attack separation (`docs/benchmarks/batadal-check.md`).
