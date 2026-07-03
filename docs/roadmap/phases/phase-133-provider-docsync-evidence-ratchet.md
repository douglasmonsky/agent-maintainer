# Phase 133: Provider DocSync Evidence Ratchet

Status: complete

## Goal

Extend DocSync dogfooding for provider documentation by linking current
TypeScript maturation and provider-status claims to durable source and test
evidence.

## Scope

- Add DocSync evidence for TypeScript real-repo reviewability tests added in
  Phase 131.
- Add DocSync evidence from the active provider registry showing Go is not active
  on `main`.
- Add trace claims tying provider docs to the new evidence.
- Ratchet provider DocSync tests so future provider-doc changes keep this
  evidence coverage.

## Non-goals

- Do not add provider behavior.
- Do not add new ecosystem providers.
- Do not promote TypeScript/JavaScript out of experimental status.
- Do not add TypeScript blocking gates.

## Acceptance Criteria

- DocSync trace contains a claim for TypeScript real-repo reviewability evidence.
- DocSync trace contains a claim for no-active-Go provider status.
- Provider DocSync tests assert that the claims and evidence IDs exist.
- `docsync check` passes.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docsync tests/docs \
  tests/assess/test_typescript_real_repo_reviewability.py \
  tests/catalogs/test_provider_registry.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
