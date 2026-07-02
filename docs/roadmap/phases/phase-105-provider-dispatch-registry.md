# Phase 105: Provider Dispatch Registry

## Status

Complete.

## Goal

Move provider-specific file classification and advisory suppression dispatch
behind the internal ecosystem registry. This keeps the TypeScript maturation
track from spreading direct imports through assessment code while preserving
current Python and TypeScript behavior.

## Scope

- Add internal registry helpers for built-in classification providers.
- Add internal registry helpers for advisory suppression providers.
- Update changed-file classification to ask the registry for candidates.
- Update `assess reviewability` suppression discovery to ask the registry.
- Preserve current Python classification, TypeScript classification, and
  TypeScript advisory suppression output.
- Keep registry private/internal; no external plugin API.

## Non-Goals

- No new language provider.
- No TypeScript blocking gates.
- No config schema changes.
- No public provider plugin loading.
- No change to Python-backed blocking reviewability gates.

## Acceptance Criteria

- `file_changes.py` no longer imports Python or TypeScript classification
  modules directly.
- `assess/reviewability.py` no longer imports TypeScript suppression modules
  directly.
- Focused tests prove TypeScript classification and suppression advisories are
  unchanged.
- Registry tests cover classification/suppression provider availability.
- Existing provider docs remain honest that TypeScript reviewability is
  advisory only.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/catalogs/test_provider_registry.py tests/ecosystems/test_file_changes.py tests/ecosystems/test_typescript_classification.py tests/ecosystems/test_typescript_suppressions.py tests/assess/test_reviewability_advisories.py tests/assess/test_typescript_reviewability_fixtures.py -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`

## Notes For Future Codex Tasks

Keep this as a registry-owned dispatch cleanup, not a provider API release.
If a future provider needs classification or suppressions, add it to the
internal registry first and prove advisory output with fixtures before any
blocking policy change.
