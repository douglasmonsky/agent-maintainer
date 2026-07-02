# Phase 98: TypeScript/Go Reviewability Fixture Evidence

## Status

Complete.

## Goal

Move the polyglot path into evidence mode before adding more provider breadth or
blocking gates. Prove that advisory TypeScript/JavaScript and Go reviewability
reports see the right changed-file shapes and suppression risks, including
dependency files that Python change-budget policy intentionally ignores.

## Scope

- Add fixture-style tests for TypeScript/JavaScript and Go changed-file roles.
- Cover source-only changes, test-backed changes, generated files,
  dependency/lockfile changes, config-only changes, broad suppressions, and
  narrow suppressions.
- Split advisory reviewability change collection from the Python change-budget
  filter so lockfiles and non-Python dependencies stay visible.
- Preserve Python-backed blocking reviewability gates.
- Keep TypeScript/JavaScript and Go reviewability findings advisory only.

## Non-Goals

- No new ecosystem provider.
- No public plugin API.
- No package-manager or workspace autodetection.
- No TypeScript/Go blocking budgets.
- No change to Python `change-budget`, `file-length`, `structure-cohesion`, or
  `suppression-budget` behavior.
- No Go structured repair facts in this phase.

## Acceptance Criteria

- Advisory reviewability tests prove TypeScript/JavaScript dependency files such
  as `package-lock.json` and Go dependency files such as `go.sum` remain visible
  to provider classification.
- Advisory reviewability tests prove TypeScript/JavaScript and Go broad
  suppressions are reported without blocking.
- Generated and ignored files do not create suppression findings.
- The neutral git change reader has tests proving it does not inherit Python
  change-budget path exclusions.
- Docs continue to state that blocking reviewability remains Python-backed.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/ecosystems tests/assess -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`

## Result

Implemented with a neutral `agent_maintainer.ecosystems.git_changes` reader
used by advisory reviewability assessment. Added fixture-style tests proving
TypeScript/JavaScript lockfiles and Go dependency files stay visible, broad
TypeScript/Go suppressions remain advisory, and generated files do not create
suppression findings.

## Notes For Future Codex Tasks

Do not widen blocking policy from fixture evidence alone. Use this phase to
separate neutral observation from Python policy filters. Later phases can add
advisory thresholds only after the fixture output proves low-noise.
