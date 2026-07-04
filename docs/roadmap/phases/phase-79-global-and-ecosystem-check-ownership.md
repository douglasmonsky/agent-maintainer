# Phase 79: Global And Ecosystem Check Ownership

## Status

Complete when this PR merges.

## Goal

Separate language-neutral/global check builders from ecosystem-owned check
builders while preserving the exact current verifier behavior.

## Scope

- Move reviewability, architecture, and workflow check builders out of the
  central catalog into a global-check catalog module.
- Keep `catalog.make_checks()` as the final composition and ordering point.
- Keep Python-owned checks behind the internal Python provider from Phase 78.
- Keep docs/config and generic security catalog helpers as global catalog
  helpers.

## Non-Goals

- No check order changes.
- No check name, profile, command, artifact, or skip-status changes.
- No new language support.
- No policy-check generalization through classifiers yet.
- No public provider API or plugin loading.

## Acceptance Criteria

- Phase 77 characterization tests pass unchanged.
- The central catalog reads as composition rather than check-construction
  detail.
- Global check ownership is explicit in Tach contracts and an ADR if
  architecture policy changes.
- Existing verifier profiles pass.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/catalogs -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```

Before merge, run one broad local profile by default; use CI-equivalent instead when diff/base-ref, workflow, or profile behavior changed. Run both only when that overlap is under test. Run security or manual when touching those gates, before release, or when explicitly requested.

## Notes For Future Codex Tasks

This phase should make ownership easier to see, not introduce new semantics. If
the extraction requires renaming checks or changing provider behavior, stop and
split the work.
