# Phase 123: Internal Package Refactor Docs Closure

Status: complete

## Goal

Close the stale recovery gap in the internal-package refactor docs after the
extraction phases landed. Future agents should see the current package shape and
remaining invariants, not instructions that imply Phase 0 still needs to start.

## Scope

- Rewrite `docs/roadmap/internal-package-boundaries.md` as a current-state
  closure note.
- Mark the exact implementation guide as archived historical context.
- Clarify that DocSync owns the docs/evidence boundary and `docs_evidence`
  should not be recreated.
- Preserve the original guide as reference material instead of deleting it.
- Keep this documentation-only.

## Non-goals

- Do not move runtime code.
- Do not change package boundaries.
- Do not alter Tach contracts.
- Do not add or remove DocSync claims.
- Do not change generated guidance.

## Acceptance Criteria

- The roadmap states that internal-package extraction phases have landed.
- The guide warns readers not to execute old examples literally.
- Current package names include `docsync`, not `docs_evidence`.
- Future work is framed as separate phase-scoped cleanup, not a restart of the
  original extraction plan.
- Docs and precommit checks pass.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docs/test_roadmap_docs.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
