# Phase 135: Remaining Active Docs DocSync Coverage

Status: complete

## Goal

Finish the current DocSync dogfooding pass by giving every active
documentation overview object at least one evidence-backed claim.

## Scope

- Add claims for active docs that still only had overview markers.
- Reuse durable implementation, test, workflow, or fixture evidence where
  possible.
- Add narrow evidence regions for docs whose behavior is not already traced.
- Ratchet tests so future active docs cannot be added without claim coverage.

## Non-goals

- Do not rewrite public docs in this phase.
- Do not change runtime behavior.
- Do not add provider behavior, scanner behavior, or new ecosystems.
- Do not create weak claims backed only by the same prose section.

## Acceptance Criteria

- `.docsync/trace.yml` has claim coverage for every active doc overview path.
- New claims point to explicit implementation, test, workflow, or fixture
  evidence.
- Public DocSync tests fail if an active doc lacks an evidence-backed claim.
- `docsync check` passes.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docsync tests/docs -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
