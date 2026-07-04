# Phase 81: Policy Checks Through Python Classifier Adapters

## Status

Complete when this PR merges.

## Goal

Move Python-specific path decisions in policy checks behind the internal Python
ecosystem classifier while preserving current Python behavior.

## Scope

- Add small Python classification predicate helpers for policy checks.
- Adapt change-budget source/test classification to use the Python classifier.
- Adapt file-length generated and ignored-file decisions to use the Python
  classifier while preserving existing helper names.
- Adapt suppression-budget Python-file filtering to use the Python classifier.
- Adapt structure-cohesion Python file discovery to use the Python classifier.
- Keep current CLI commands, output wording, profile behavior, and config
  semantics unchanged.

## Non-Goals

- No TypeScript or other new ecosystem support.
- No public provider API.
- No neutral config-file migration.
- No check rename or verifier output contract change.
- No broad policy rewrite beyond classifier adapter use.

## Acceptance Criteria

- Phase 77 characterization tests still pass.
- Existing policy tests still pass.
- Check commands and profile membership remain unchanged.
- Tach exact validates the new dependency direction.
- Any Tach policy change has an architecture decision note.

## Verification

Run focused policy tests:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m pytest tests/checks tests/catalogs/test_python_catalog_characterization.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/tach check --exact
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m agent_maintainer verify --profile precommit
```

Before merge, run one broad local profile by default; use CI-equivalent instead when diff/base-ref, workflow, or profile behavior changed. Run both only when that overlap is under test. Run security or manual when touching those gates, before release, or when explicitly requested.

## Notes For Future Codex Tasks

Use narrow adapters instead of forcing policy checks into a generic
lowest-common-denominator model. If a classifier abstraction makes current
Python policy behavior harder to express, stop and redesign it.
