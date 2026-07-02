# Phase 78: Minimal Internal Python Provider Seam

## Status

Complete when this PR merges.

## Goal

Introduce the smallest internal ecosystem-provider seam and move Python check
generation behind a Python provider without changing observable behavior.

## Scope

- Add private/internal ecosystem provider models only as needed.
- Add a built-in Python provider that emits the current Python check objects.
- Keep `catalog.make_checks()` responsible for orchestration and final ordering.
- Keep current check names, profile memberships, key commands, artifact paths,
  optional skips, config semantics, and CLI behavior intact.

## Non-Goals

- No TypeScript, JavaScript, Go, Rust, Java, or other new language support.
- No external plugin API or entry point discovery.
- No config migration.
- No check renames.
- No provider ownership of diagnostics, hook clients, reporting, or verifier
  execution.
- No broad policy-check generalization; that belongs to a later phase.

## Acceptance Criteria

- Phase 77 characterization tests pass unchanged.
- `catalog.make_checks()` remains the integration point used by verifier code.
- Python check generation is reachable through an internal Python provider.
- No public API stability is promised for the provider seam.
- Normal verifier profiles still pass.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  tests/catalogs/test_python_catalog_characterization.py \
  tests/checks/test_python_policy_characterization.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/catalogs -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```

Before merge, run the broader local gates or rely on PR CI only if the change is
still clearly behavior-preserving and the narrow characterization suite is
complete.

## Notes For Future Codex Tasks

If a proposed provider abstraction makes an existing Python feature harder to
express, stop and redesign the abstraction. Python remains the reference
provider and should become more organized, not less capable.
