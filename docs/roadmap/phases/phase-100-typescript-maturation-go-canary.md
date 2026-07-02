# Phase 100: TypeScript Maturation And Go Canary Freeze

## Status

Complete.

## Goal

Make TypeScript/JavaScript the first serious non-Python provider maturation
track while keeping Go as a thin experimental canary. This keeps provider design
honest across more than one non-Python ecosystem without splitting depth work
across multiple incomplete providers.

## Scope

- Keep Python as the core/reference provider and preserve current behavior.
- Keep Go experimental, explicit-command-only, and useful for registry,
  classifier, doctor, and advisory-report compatibility checks.
- Freeze Go depth expansion unless a maintenance fix is required by shared
  provider infrastructure.
- Add TypeScript/JavaScript fixture evidence for common repository shapes:
  basic npm package, pnpm workspace, Vite/Vitest, Jest, generated folders,
  source-only changes, source-plus-test changes, dependency changes, config
  changes, and broad/narrow suppressions.
- Improve TypeScript/JavaScript repair facts only for stable, documented tool
  outputs.
- Add a running TypeScript provider maturation note or case study that records
  what generalized cleanly and what stayed ecosystem-specific.
- Consider advisory TypeScript thresholds only after fixture and real-repo output
  proves low-noise.

## Non-Goals

- No new ecosystem provider.
- No public plugin API.
- No Go starter files.
- No Go coverage adapter.
- No Go structured repair facts.
- No Go dependency/security adapter.
- No Go workspace behavior.
- No TypeScript/JavaScript blocking gates.
- No package-manager autodetection until explicit-command behavior is proven.
- No changes to Python check names, commands, artifacts, thresholds, or profiles.

## Acceptance Criteria

- Provider docs state TypeScript/JavaScript is the first maturation candidate and
  Go is a canary, not a parallel depth track.
- TypeScript fixture tests cover representative source/test/generated/config,
  dependency, and suppression scenarios.
- Go tests continue proving registry/classifier/advisory compatibility without
  adding deeper Go features.
- TypeScript repair-fact additions are backed by stable sample outputs.
- Any TypeScript thresholds are advisory-only and disabled from blocking
  verifier profiles.
- No new language is added.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/ecosystems tests/assess -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`

## Notes For Future Codex Tasks

If an abstraction makes Python less capable, stop and redesign it. If a
TypeScript improvement pushes Node/package-manager assumptions into core, move
that behavior back behind the TypeScript provider. If a Go change starts looking
like a new depth track, defer it unless it protects shared provider boundaries.

## Result

Added TypeScript fixture-style reviewability tests covering source-plus-test
changes, source-only heavy changes, generated/build outputs, dependency files,
config files, and broad/narrow suppressions. Added TypeScript provider
maturation notes under `docs/case-studies/` and kept Go canary-only: no Go
starter files, repair facts, coverage, dependency/security adapters, workspace
behavior, or blocking gates were added.
