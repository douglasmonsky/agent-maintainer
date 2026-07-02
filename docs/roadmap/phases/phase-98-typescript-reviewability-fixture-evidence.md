# Phase 98: TypeScript Reviewability Fixture Evidence

## Status

Complete.

## Goal

Move the polyglot path into evidence mode before adding more provider breadth or
blocking gates. Prove advisory TypeScript/JavaScript reviewability reports the
right changed-file shapes, suppression risks, dependency files, and files that
Python change-budget policy intentionally ignores.

## Scope

- Add fixture-style tests for TypeScript/JavaScript changed-file roles.
- Cover source-only changes, test-backed changes, generated files,
  dependency/lockfile changes, config-only changes, broad suppressions, and
  narrow suppressions.
- Split advisory reviewability change collection from the Python change-budget
  filter so non-Python dependency files stay visible.
- Preserve Python-backed blocking reviewability gates.
- Keep TypeScript/JavaScript reviewability findings advisory only.

## Non-Goals

- No new ecosystem provider.
- No public plugin API.
- No package-manager or workspace autodetection.
- No TypeScript/JavaScript blocking budgets.
- No change to Python `change-budget`, `file-length`, `structure-cohesion`, or
  `suppression-budget` behavior.

## Acceptance Criteria

- Advisory reviewability tests prove TypeScript/JavaScript dependency files
  such as `package-lock.json` remain visible to provider classification.
- Advisory reviewability tests prove TypeScript/JavaScript broad suppressions
  are reported without blocking.
- Generated ignored files do not create suppression findings.
- Neutral git change reader tests prove advisory assessment does not inherit
  Python change-budget path exclusions.
- Docs continue to state that blocking reviewability remains Python-backed.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/ecosystems tests/assess -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`

## Result

Added fixture-style advisory reviewability coverage for TypeScript/JavaScript
source, test, generated, dependency, config, and suppression scenarios. The
output remains advisory and does not widen Python-backed blocking gates.
