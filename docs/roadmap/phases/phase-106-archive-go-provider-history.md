# Phase 106: Archive Go Provider History Out Of Main

## Status

Complete.

## Goal

Remove Go-provider experiment artifacts from the active `main` branch while
preserving the experiment on `archive/go-provider-experiment`. Agent Maintainer
should stay Python-core with TypeScript/JavaScript as the only active
experimental non-Python provider until that path has stronger evidence.

## Scope

- Keep the existing `archive/go-provider-experiment` branch as the preservation
  point for Go-provider work.
- Remove Go-specific provider roadmap phase docs from active `main`.
- Remove Go-specific architecture decision notes that described implemented
  provider behavior.
- Rewrite mixed TypeScript/Go roadmap and policy docs to TypeScript-focused
  language where the TypeScript content remains useful.
- Remove active provider-status and case-study language that describes Go as a
  deferred canary.
- Replace test fixtures that use `.go`, `go.mod`, or `go.sum` as provider
  evidence with neutral unsupported-ecosystem examples.
- Preserve generic polyglot examples where they describe future possible
  ecosystems rather than the removed experiment.

## Non-Goals

- No TypeScript/JavaScript behavior changes.
- No Python behavior changes.
- No new provider implementation.
- No external plugin API.
- No deletion of the off-main archive branch.
- No claim that Go will never be supported.

## Acceptance Criteria

- Active source and tests contain no Go-provider config, provider, command, or
  fixture contract.
- Public provider-status docs list Python and TypeScript/JavaScript only.
- Roadmap index no longer links Go-specific phase files.
- Go-specific experiment ADRs and phase files are removed from active `main`.
- Generic future-language examples may still mention Go only as a possible
  future ecosystem, not as existing support or a deferred canary.
- Focused docs and provider tests pass.

## Verification

- `rg -n "enable_go|go_format|go_vet|go_test|GoProvider|go-format|go-vet|go-test" src tests docs pyproject.toml config`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/catalogs/test_provider_registry.py tests/ecosystems tests/assess -q`
- `npx --no-install markdownlint-cli2 docs/ROADMAP.md docs/roadmap/full-roadmap-blueprint.md docs/roadmap/phases/phase-106-archive-go-provider-history.md docs/provider-status.md docs/multi-ecosystem-reviewability-policy.md`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check`

## Notes For Future Work

Reintroduce Go only through a fresh numbered roadmap phase after
TypeScript/JavaScript reaches a stronger supported-experimental bar. Start from
the archive branch if useful, but treat that code as design reference rather
than accepted mainline behavior.
