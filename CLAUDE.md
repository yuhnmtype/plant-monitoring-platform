# CLAUDE.md

Project: plant-monitoring-platform. A generic plant monitoring platform built and evaluated on simulated data only. Read README.md, docs/problem-brief.md and docs/timeline.md before planning work.

## Rules that always apply
- Do not commit, tag or push until Huy sends "xong" as a standalone message. Before any commit, report `git branch --show-current` and `git status --short`, and stage files by name.
- Show every change as a text diff in your reply.
- Never read or print environment variables. No secrets, keys, tokens or real credentials in the repo. `.env` stays untracked; only `.env.example` with empty values is committed.
- Run checks yourself (venv, installs into the project venv, pytest, ruff) and paste the raw output. Ask Huy only when you cannot run something. Still ask before global or system-wide installs, adding dependencies that are not decided yet, and touching files outside this repo.
- Say what you ran versus what you inferred. Do not invent numbers or facts.
- Do not change permission modes or other settings yourself.

## Honesty
- All data is simulated and must be labelled so. Never claim real industrial (OT) experience, real plants or real users.
- README and CV claims only for milestones marked Done in the README status table.
- Negative results get the same prominence as positive ones.

## Frozen files
- docs/evaluation-criteria-v1.md is a DRAFT until the git tag `eval-criteria-v1` exists (end of M1). After the tag never edit it, not even typos: corrections go to an errata file, and changed criteria become a labelled v2.

## Layout and boundaries
- Core = `src/plantmon/` and `db/`. Profiles = `profiles/`.
- Core stays plant-agnostic: no water or engine terms in core code, schema or tests. Everything plant-specific is data in a profile (YAML or rows).
- Success criterion: adding profile 2 (engine test cell) changes zero lines under the core paths. If a core change seems needed, stop and ask Huy; every such change is recorded with its reason.
- Detectors never read the incident-label table; only the evaluation code does.
- The dashboard reads data only through the API layer (ADR 0003 and 0005).
- BATADAL files are never committed; a script downloads them into a git-ignored folder (docs/benchmarks/batadal-check.md).

## Process
- New ideas go to docs/backlog.md first (three triage questions). Do not implement an idea that is not in the current milestone's spec.
- Before implementing a new idea, ask open questions with a few options, the reason for each and a recommended one.
- No new features after M6.
- Each milestone has "must" and "if time" items written in its spec before it starts. A slipped milestone shrinks the next one; nothing is dropped silently.

## Commands (Windows PowerShell, from the repo root)
- Install: `python -m venv .venv`, then `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`
- Test: `.\.venv\Scripts\python.exe -m pytest`
- Lint: `.\.venv\Scripts\python.exe -m ruff check .`

## Language
Code, comments, docs and commit messages are in English. When explaining to Huy, reply in Vietnamese.
