# Phase 167: React/Vite/Next Structured Test And Coverage Facts

Status: complete

## Goal

Add structured TypeScript/React test and coverage repair facts for stable
React/Vite/Next-adjacent outputs without adding framework command inference,
coverage enforcement, or blocking TypeScript gates.

## Scope

- Extend `typescript-test` compact summaries and exact repair facts for Vitest
  task-style JSON.
- Add `typescript-test` artifact facts for Istanbul `coverage-summary.json`.
- Add `typescript-test` artifact facts for LCOV `lcov.info` and `.lcov` files.
- Keep malformed or arbitrary human-oriented transcripts on the existing
  bounded raw-log fallback path.
- Update TypeScript provider and maturation docs with the supported artifact
  shapes and remaining limitations.

## Non-Goals

- No package-manager autodetection.
- No Vite, Next.js, Jest, Vitest, React, or Node command execution.
- No TypeScript coverage command adapter or threshold gate.
- No framework-specific generated-file policy.
- No blocking reviewability gate or provider promotion.

## Acceptance Criteria

- `typescript-test` can extract file, line, test name, and concise failure
  messages from Vitest task-style JSON.
- `typescript-test` can extract coverage facts from Istanbul
  `coverage-summary.json` and LCOV artifacts.
- Existing Jest-compatible JSON, ESLint JSON, and TypeScript compiler facts keep
  working.
- Docs clearly state this is parser evidence only, not TypeScript coverage
  enforcement or framework command support.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/core/test_typescript_structured_output.py tests/context/test_typescript_exact_facts.py tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
