# Phase 83: Experimental TypeScript/JavaScript Provider

## Status

Complete in this PR.

## Goal

Add the first non-Python ecosystem provider as an explicit, experimental,
configured-command provider while preserving Python as the reference provider
and keeping current Python behavior unchanged.

## Scope

- Add an internal TypeScript/JavaScript provider under
  `agent_maintainer.ecosystems.typescript`.
- Add file classification for common TypeScript and JavaScript source, test,
  generated, config, dependency, docs, and ignored paths.
- Add disabled-by-default config fields for enabling the provider and supplying
  lint, typecheck, and test commands.
- Add catalog integration so enabled TypeScript checks appear in normal
  verifier profiles.
- Add focused tests proving default catalog behavior remains unchanged and
  configured TypeScript commands are respected.
- Add Tach ownership and an ADR for the new internal provider boundary.

## Non-Goals

- No package-manager autodetection.
- No starter-file generation for TypeScript repositories.
- No TypeScript-specific doctor rows.
- No structured TypeScript artifact parsers.
- No TypeScript coverage, mutation, dependency, or security adapter.
- No public plugin API.
- No Python check weakening, renaming, or command changes.

## Design Rules

- Core owns the verification loop, logs, artifacts, summaries, hooks, reports,
  context packs, and repair-loop output.
- Providers own ecosystem knowledge.
- Python remains the core/reference provider and must stay free to express
  Python-specific excellence.
- The TypeScript provider starts smaller than Python on purpose. It should
  prove the provider seam without forcing a lowest-common-denominator model.
- If a provider abstraction makes a Python feature harder to express, stop and
  redesign the abstraction.

## Acceptance Criteria

- `enable_typescript = false` remains the default and produces no TypeScript
  checks.
- `enable_typescript = true` with explicit commands creates
  `typescript-lint`, `typescript-typecheck`, and `typescript-test` checks.
- Missing enabled commands are reported as optional skips, not guessed.
- TypeScript check profile lists are configurable.
- Python catalog characterization tests still pass.
- TypeScript file classification is tested.
- Tach assigns every new provider file explicitly.
- No external plugin loading is introduced.

## Verification

Run focused checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m pytest \
  tests/ecosystems/test_typescript_classification.py \
  tests/ecosystems/test_typescript_provider.py \
  tests/catalogs/test_typescript_catalog.py \
  tests/config/test_typescript_config.py \
  tests/catalogs/test_python_catalog_characterization.py \
  tests/catalogs/test_global_catalog_characterization.py \
  tests/config/test_config_metadata.py -q

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/tach check --exact

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m agent_maintainer verify --profile precommit
```

Before merge, run one broad local profile by default; use CI-equivalent instead when diff/base-ref, workflow, or profile behavior changed. Run both only when that overlap is under test. Run security or manual when touching those gates, before release, or when explicitly requested.

## Follow-Up

Phase 84 should add TypeScript doctor hints and scaffold fixtures only after
Phase 83 proves the internal provider seam does not disturb Python behavior.
