# Phase 174: TypeScript Workspace Command Config

Status: active

## Goal

Add explicit workspace-owned TypeScript command configuration without recursive
package discovery or package-manager inference.

## Scope

- Load TypeScript command arrays from named workspace config tables.
- Emit package-owned TypeScript checks only when workspace commands are
  explicitly configured.
- Keep root TypeScript command behavior unchanged.
- Update setup-advisor and provider docs for the explicit ownership surface.

## Non-Goals

- No nested package scanning.
- No workspace manager inference.
- No command body parsing.
- No workspace-specific profile matrix.
- No TypeScript gate promotion to blocking status.

## Acceptance Criteria

- Workspace config can load `typescript_lint_command`,
  `typescript_typecheck_command`, and `typescript_test_command`.
- TypeScript provider emits stable workspace check names for configured
  commands.
- Missing workspace commands do not create extra skipped checks.
- Public docs tell users this is explicit command ownership, not discovery.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/config/test_workspace_config.py tests/catalogs/test_typescript_catalog.py tests/docs/test_first_touch_docs.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m tach check --exact
```
