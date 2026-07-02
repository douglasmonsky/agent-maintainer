# Phase 87: Experimental Go Provider

## Status

Complete in PR. Superseded by
[`phase-103-defer-go-provider.md`](phase-103-defer-go-provider.md).

## Goal

Add a second non-Python experimental provider to validate the internal provider
seam outside Node-style ecosystems without changing Python behavior or
publishing an external plugin API.

## Scope

- Add disabled-by-default Go provider check generation.
- Add explicit-command checks:
  - `go-format`;
  - `go-vet`;
  - `go-test`.
- Add Go file classification.
- Add config and environment variable support for Go provider commands and
  profile membership.
- Add focused tests for config, classifier, provider, and catalog integration.
- Add Go provider docs.
- Update Tach domain contracts and ADR for provider boundary ownership.

## Non-Goals

- No default-enabled Go checks.
- No command autodetection.
- No generated Go starter files.
- No structured Go output parser.
- No Go coverage, mutation, dependency, or security adapter.
- No public provider API.

## Acceptance Criteria

- `enable_go = false` remains default and produces no Go checks.
- `enable_go = true` with explicit commands creates `go-format`, `go-vet`,
  and `go-test`.
- Empty enabled command fields produce optional skips.
- Go classifier covers source, tests, generated files, dependency files,
  config files, docs, and ignored paths.
- Existing Python and TypeScript behavior is unchanged.
- Tach exact check passes.

## Verification

Run focused checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m pytest \
  tests/ecosystems/test_go_classification.py \
  tests/ecosystems/test_go_provider.py \
  tests/catalogs/test_go_catalog.py \
  tests/config/test_go_config.py \
  tests/config/test_config_metadata.py \
  -q
```

Run architecture and docs checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  node_modules/.bin/markdownlint-cli2 \
    docs/roadmap/phases/phase-87-experimental-go-provider.md \
  docs/roadmap/polyglot-ecosystem-providers.md \
  docs/roadmap/full-roadmap-blueprint.md \
  docs/ROADMAP.md
```

Before merge, run standard verifier profiles once.
