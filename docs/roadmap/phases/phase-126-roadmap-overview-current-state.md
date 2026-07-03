# Phase 126: Roadmap Overview Current State

Status: complete

## Goal

Refresh `docs/roadmap/overview.md` so it describes the current beta product
state instead of an older context-safe-ratchet implementation prompt.

## Scope

- Rewrite the overview as current-state orientation.
- Include current baseline capabilities, provider posture, internal packages,
  DocSync, repair capsule behavior, and verification rules.
- Add a test guard against stale "next major product layer" implementation
  prompt language returning.
- Keep this documentation/test-only.

## Non-goals

- Do not alter runtime behavior.
- Do not change roadmap phase scope.
- Do not add new providers.
- Do not change generated guidance.

## Acceptance Criteria

- The overview describes current baseline capabilities.
- The overview states Python is core/reference and TypeScript/JavaScript is
  experimental.
- The overview keeps graph/vector/GraphQL work out of normal scope.
- The overview does not describe legacy-ratchet work as the next major product
  layer.
- Docs checks and precommit pass.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docs/test_roadmap_docs.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
