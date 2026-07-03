# Phase 130: Public First-Touch Docs Prose Polish

Status: complete

## Goal

Polish the public first-touch documentation so new users can understand install,
verification, diagnostics, and the agent-context model without parsing compressed
prose or collapsed shell examples.

## Scope

- Improve README opening sections and quick-start command blocks.
- Polish `docs/quick-start.md`.
- Polish context-safety and diagnostics-repair-loop docs.
- Polish the human-readable generated-guidance explainer.
- Keep product behavior unchanged.
- Preserve existing DocSync object markers and claim coverage.

## Non-goals

- Do not rewrite the entire documentation set.
- Do not add new checks, scanners, profiles, or runtime behavior.
- Do not change generated `AGENTS.agent-maintainer.md` unless guidance
  generation changes.
- Do not expand DocSync claim/evidence coverage beyond the affected docs in this
  phase.

## Acceptance Criteria

- First-touch docs use complete sentences and readable command blocks.
- Context-pack docs clearly state pointer-first behavior and the `--print-full`
  escape hatch.
- Diagnostics docs clearly describe run-scoped artifacts and `LAST_FAILURE.md`
  as a convenience pointer.
- DocSync check passes.
- Public docs tests and precommit pass.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docs tests/docsync -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
