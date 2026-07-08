# Phase 173: TypeScript Workspace Command Ownership Design

Status: active

## Goal

Define workspace command ownership semantics before setup advisor or the
TypeScript provider recursively recommend nested package commands.

## Scope

- Document that root TypeScript commands must intentionally cover packages.
- Document package-specific checks as manual follow-up until ownership exists.
- Add public-doc phrase coverage for the new TypeScript provider boundary.
- Keep roadmap and DocSync trace aligned with the design boundary.

## Non-Goals

- No recursive package discovery.
- No workspace manager inference.
- No command body parsing.
- No new configuration schema for package ownership.
- No TypeScript gate promotion to blocking status.

## Acceptance Criteria

- Provider docs describe manual workspace command ownership.
- Setup-advisor docs tell users to configure root commands only when they cover
  intended packages.
- Maturation notes include workspace command ownership before recursive package
  discovery in the promotion bar.
- Public-doc tests cover the new provider and maturation wording.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m tach check --exact
```
