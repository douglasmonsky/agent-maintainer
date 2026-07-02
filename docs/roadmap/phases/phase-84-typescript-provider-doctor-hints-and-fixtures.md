# Phase 84: TypeScript Provider Doctor Hints And Fixture Smoke Tests

## Status

Complete in this PR.

## Goal

Add setup-health hints and fixture-style tests for the experimental
TypeScript/JavaScript provider without changing default Python behavior,
autodetecting package managers, or generating TypeScript starter files.

## Scope

- Add doctor checks for enabled TypeScript provider configuration.
- Report missing configured commands as setup warnings with concrete repair
  hints.
- Report missing configured command executables as missing tooling warnings.
- Keep disabled TypeScript provider silent in doctor output.
- Add fixture/smoke tests that model a minimal TypeScript-enabled repository
  config and prove catalog/doctor behavior.
- Update TypeScript provider docs to mention doctor behavior.

## Non-Goals

- No package-manager autodetection.
- No generated TypeScript starter files.
- No scaffold command changes.
- No structured ESLint, TypeScript, Jest, Vitest, or coverage parser.
- No TypeScript security, dependency, or coverage gate.
- No public provider API.

## Acceptance Criteria

- `doctor` has no TypeScript row when `enable_typescript = false`.
- `doctor` warns when `enable_typescript = true` but no commands are configured.
- `doctor` warns when a configured command's executable is unavailable.
- `doctor` passes when enabled commands point to available executables.
- Fixture-style tests prove a minimal TypeScript-enabled config produces
  expected catalog checks without affecting Python characterization.
- Docs state TypeScript provider remains explicit-command and experimental.

## Verification

Run focused checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m pytest \
  tests/doctor/test_typescript_doctor.py \
  tests/ecosystems/test_typescript_provider.py \
  tests/catalogs/test_typescript_catalog.py -q

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/tach check --exact
```

Before merge, run the standard verifier profiles once.
