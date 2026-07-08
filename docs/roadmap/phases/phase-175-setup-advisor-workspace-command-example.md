# Phase 175: Setup Advisor Workspace Command Example

Status: active

## Goal

Show users how to configure explicit workspace-owned TypeScript commands from
setup-advisor guidance without implying nested package discovery.

## Scope

- Extend the TypeScript setup-advisor recommendation with workspace command
  config guidance.
- Add a concrete workspace command TOML example to setup-advisor docs.
- Add focused tests for the new recommendation wording and public docs.
- Keep roadmap and DocSync trace aligned.

## Non-Goals

- No nested package scanning.
- No workspace manager inference.
- No command body parsing.
- No TypeScript provider runtime change.
- No TypeScript gate promotion to blocking status.

## Acceptance Criteria

- Setup advisor TypeScript recommendations mention
  `[tool.agent_maintainer.workspaces.<name>]` for package-specific checks.
- Setup-advisor docs include a workspace-owned TypeScript command example.
- Public-doc tests cover the new example wording.
- DocSync trace remains fresh.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_setup_advisor.py tests/docs/test_first_touch_docs.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m tach check --exact
```
