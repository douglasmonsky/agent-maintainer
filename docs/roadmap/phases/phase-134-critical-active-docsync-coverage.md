# Phase 134: Critical Active Docs DocSync Coverage

Status: complete

## Goal

Keep moving toward full DocSync dogfooding by giving high-risk active docs
evidence-backed claims, not only overview markers.

## Scope

- Add DocSync claims for active docs that steer agent behavior or public trust:
  agent guidance, setup advisor, technical debt score, mutation testing, context
  safety, and multi-ecosystem reviewability.
- Reuse durable implementation and test evidence where possible.
- Ratchet the public DocSync tests so these claims remain required.

## Non-goals

- Do not rewrite the docs in this phase.
- Do not change runtime behavior.
- Do not add new provider behavior or new ecosystem support.
- Do not claim every active doc has section-level claim coverage yet.

## Acceptance Criteria

- `.docsync/trace.yml` contains claims for the selected critical active docs.
- Each new claim points to implementation or test evidence.
- Public DocSync tests require the new claims.
- `docsync check` passes.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docsync tests/docs -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
