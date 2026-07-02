# Phase 103: Defer Go Provider From Active Surface

## Status

Complete.

## Goal

Remove Go from Agent Maintainer's active provider surface while preserving the
provider architecture lesson it supplied. TypeScript/JavaScript should become
the first serious non-Python provider track. Go should be deferred until
TypeScript fixture and real-repo evidence proves the provider model is ready for
another ecosystem.

## Rationale

There are no public Go adopters yet, so backward compatibility is not a
constraint. Keeping Go active in `main` creates config, docs, tests, doctor, and
reviewability maintenance work while the current product focus should be
TypeScript maturation. A long-lived Go branch would rot outside CI, so the
cleaner move is to remove active Go code from `main` and leave the roadmap and
provider docs clear that Go is deferred, not supported.

## Scope

- Remove active Go provider registration, Go checks, Go config fields, and Go
  doctor rows from `main`.
- Remove Go-specific classification and suppression dispatch from active
  advisory reviewability.
- Remove Go-focused tests that only protect the deferred active provider.
- Update docs to say TypeScript/JavaScript is the first non-Python maturation
  target and Go is deferred until after TypeScript reaches a stronger maturity
  bar.
- Keep historical roadmap/ADR context where useful, but do not advertise Go as
  an active provider.

## Non-Goals

- No TypeScript blocking gates.
- No new ecosystem provider.
- No external plugin API.
- No package-manager autodetection.
- No change to Python provider behavior.
- No archival branch as a substitute for tested mainline state.

## Acceptance Criteria

- Provider registry exposes Python and TypeScript/JavaScript only.
- Config schema no longer exposes active Go enable/command fields.
- `assess reviewability` no longer imports Go classification or suppression
  modules.
- Public docs and provider status no longer present Go as an active
  experimental provider.
- Tests cover Python and TypeScript provider behavior after removal.
- Existing OSV/setup evidence for `go.mod` may remain as generic non-Python
  dependency evidence if useful, but it must not imply active Go provider
  support.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/catalogs tests/ecosystems tests/doctor tests/config tests/assess -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`

## Notes For Future Codex Tasks

If Go returns later, reintroduce it from the current provider patterns rather
than reviving stale branch code. The minimum bar should include fixtures,
doctor rows, explicit command setup, and advisory reviewability evidence.

## Result

- Removed Go from active provider metadata, provider instances, config schema,
  env loading, doctor rows, changed-file classification, and suppression
  dispatch.
- Deleted active Go provider modules, Go provider docs, and Go-only tests.
- Updated public docs to present Go as deferred and TypeScript/JavaScript as the
  only active non-Python maturation track.
- Added an ADR documenting why Go was removed from the active architecture
  instead of kept on a long-lived branch.
