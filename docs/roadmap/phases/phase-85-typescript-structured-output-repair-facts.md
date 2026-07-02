# Phase 85: TypeScript Structured Output Repair Facts

## Status

Complete in this PR.

## Goal

Add compact summaries and exact repair facts for common TypeScript provider
outputs without changing provider configuration or requiring package-manager
autodetection.

## Scope

- Parse `tsc --pretty false` style diagnostics from `typescript-typecheck` logs.
- Parse ESLint JSON output from `typescript-lint` logs.
- Feed parsed diagnostics into compact verifier summaries.
- Feed parsed diagnostics into context exact repair facts.
- Preserve existing Pyright, Ruff, Bandit, pytest, and security structured
  summary behavior.

## Non-Goals

- No new artifact-path config fields.
- No package-manager autodetection.
- No TypeScript coverage or test-result parser.
- No TypeScript security/dependency adapter.
- No public provider API.

## Acceptance Criteria

- `typescript-typecheck` failures can summarize `file(line,column): error TS...`
  diagnostics.
- `typescript-lint` failures can summarize ESLint JSON output.
- `context failures` can emit exact repair facts for TypeScript lint and
  typecheck failures.
- Malformed output falls back to existing raw-log behavior.
- Existing structured parser tests for Python/security checks still pass.

## Verification

Run focused checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m pytest \
  tests/core/test_typescript_structured_output.py \
  tests/context/test_typescript_exact_facts.py \
  tests/core/test_reporting_artifacts.py \
  tests/context/test_exact_facts.py -q
```

Before merge, run the standard verifier profiles once.
