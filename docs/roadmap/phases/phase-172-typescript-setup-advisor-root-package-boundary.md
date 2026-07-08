# Phase 172: TypeScript Setup Advisor Root Package Boundary

Status: active

## Goal

Make setup-advisor TypeScript script evidence explicitly root-package scoped so
workspace adopters do not assume nested package command ownership.

## Scope

- Add setup-advisor coverage for nested workspace package scripts.
- Document that nested workspace packages are not scanned yet.
- Keep DocSync and roadmap tracking aligned with the boundary.

## Non-Goals

- No recursive workspace package discovery.
- No package-manager or workspace manager inference.
- No command body parsing or command ownership model.
- No TypeScript gate promotion to blocking status.

## Acceptance Criteria

- Nested `packages/*/package.json` scripts alone do not trigger TypeScript
  provider setup advice.
- Root `package.json` script shapes continue to trigger advisory advice.
- Docs name the root-only limitation and still require explicit config command
  arrays.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_setup_advisor.py tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m tach check --exact
```
