# Phase 127: Git Metadata Duplicate Artifact Warning

Status: complete

## Goal

Extend the warning-only duplicate artifact doctor check to catch local
Finder-style duplicate Git metadata files such as `.git/index 2`.

## Scope

- Keep duplicate artifact handling warning-only.
- Add a shallow `.git` scan for duplicate-named files directly under `.git`.
- Do not recurse through Git internals or inspect object contents.
- Add focused doctor test coverage.
- Keep cleanup manual; users and agents must verify duplicates before deletion.

## Non-goals

- Do not delete files automatically.
- Do not scan Git object databases.
- Do not change verifier profiles.
- Do not turn this warning into a blocking CI gate for clean checkouts.

## Acceptance Criteria

- `.git/index 2` style artifacts produce a `duplicate-artifacts` warning.
- Existing generated-root duplicate warnings still work.
- Focused doctor tests pass.
- Precommit passes.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/doctor/test_doctor_environment.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
