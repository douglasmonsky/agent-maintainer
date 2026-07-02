# Phase 104: TypeScript Test Repair Facts

## Status

Complete.

## Goal

Add narrow, structured repair facts for TypeScript/JavaScript test failures
without changing provider maturity, package-manager detection, or blocking
policy. The parser should make `typescript-test` failures easier for agents to
repair while keeping raw test transcripts in run-scoped artifacts.

## Scope

- Add one parser for a stable JSON test-output shape.
- Wire the parser only into `typescript-test` exact facts and compact failure
  summaries.
- Preserve existing `typescript-lint` and `typescript-typecheck` behavior.
- Keep malformed or unrelated output on the normal bounded-log fallback path.
- Document the supported test-output shape and remaining limitations.

## Non-Goals

- No package-manager autodetection.
- No TypeScript coverage support.
- No TypeScript mutation testing.
- No blocking TypeScript reviewability gate.
- No Go provider restoration.
- No new ecosystem provider.

## Acceptance Criteria

- `typescript-test` can extract file, test name, and concise failure message
  from the supported JSON output shape.
- Parser failures never hide the original log fallback.
- Context exact facts can include TypeScript test facts.
- Docs clearly state that this is structured repair support, not provider
  parity with Python.
- Focused parser, context, and reporting tests pass.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/ecosystems tests/context tests/core -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`

## Notes For Future Codex Tasks

Prefer fixture-backed parsers over guessing framework behavior. If a parser
requires users to configure a specific reporter, document the exact command
shape instead of silently guessing.

## Result

- Added a Jest-compatible JSON parser for `typescript-test` output.
- Wired `typescript-test` into compact failure summaries and exact repair facts.
- Documented supported JSON test output and remaining limitations.
- Kept TypeScript support advisory and non-blocking.
