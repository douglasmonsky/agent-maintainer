# Phase 80: Generic File Classification, Python Only

## Status

Complete when this PR merges.

## Goal

Introduce a small internal file-role model and Python classifier that preserves
current Python source, test, generated, and ignored behavior before policy checks
start using provider/classifier adapters.

## Scope

- Add generic file classification types under the internal ecosystem package.
- Add a Python classifier that recognizes current Python source, test,
  generated, docs, config, dependency, unknown, and ignored roles.
- Add tests for current Python classification behavior.
- Keep the classifier internal and Python-only.

## Non-Goals

- No TypeScript or other new ecosystem support.
- No policy-check rewrites yet.
- No config migration.
- No CLI or verifier output changes.
- No public plugin API.

## Acceptance Criteria

- Python source/test classification matches current `source_roots` and
  `test_roots` semantics.
- Generated and ignored Python files can be identified without changing current
  file-length or structure behavior.
- Existing Phase 77 catalog characterization tests still pass.
- No runtime verifier behavior changes are required.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m pytest tests/ecosystems -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/tach check --exact
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m agent_maintainer verify --profile precommit
```

Before merge, run full, CI-equivalent, security, and manual profiles once.

## Notes For Future Codex Tasks

Phase 5 may adapt change-budget, file-length, suppression-budget, and structure
checks to consume classifiers. Do not do that in this phase unless a tiny helper
is required by tests.
