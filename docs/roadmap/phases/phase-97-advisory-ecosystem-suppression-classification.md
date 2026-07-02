# Phase 97: Advisory Ecosystem Suppression Classification

Status: planned.

## Goal

Add advisory ecosystem-specific suppression classification for
TypeScript/JavaScript and Go so `assess reviewability` can show suppression
pressure without changing the current blocking Python `suppression-budget`
gate.

## Scope

- Add internal suppression finding models for provider-owned classifiers.
- Add TypeScript/JavaScript suppression patterns such as `eslint-disable`,
  `@ts-ignore`, `@ts-expect-error`, `@ts-nocheck`, Istanbul, and c8 ignores.
- Add Go suppression patterns such as `//nolint` and `//nolint:<linter>`.
- Surface advisory suppression counts in `assess reviewability` text and JSON.
- Keep existing Python blocking suppression-budget behavior unchanged.
- Add tests proving TypeScript/JavaScript and Go suppressions are advisory only.

## Non-Goals

- No new blocking TypeScript/JavaScript or Go suppression gate.
- No change to `suppression-budget` behavior or thresholds.
- No new provider.
- No config migration.
- No external plugin API.

## Acceptance Criteria

- TypeScript/JavaScript and Go provider suppression classifiers return explicit
  suppression kind and broad/narrow status.
- `assess reviewability` reports advisory suppression counts when changed files
  contain recognized suppression lines.
- JSON output exposes suppression findings without failing the command.
- Python `suppression-budget` tests still pass.
- Current verifier profile behavior remains unchanged.

## Verification

Run focused checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  tests/ecosystems tests/assess tests/checks/test_suppression_budget.py -q
```

Run static checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m ruff check \
  src/agent_maintainer/ecosystems src/agent_maintainer/assess tests/ecosystems tests/assess
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check
```

Before PR merge, run the standard final gates.
