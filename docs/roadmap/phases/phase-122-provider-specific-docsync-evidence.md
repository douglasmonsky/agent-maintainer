# Phase 122: Provider-Specific DocSync Evidence

Status: complete

## Goal

Extend DocSync dogfooding into the provider-specific public docs that guide the
next polyglot maturation work. TypeScript/JavaScript remains the only active
non-Python maturation target, so its public docs and maturation notes should be
backed by durable source and test evidence.

## Scope

- Add DocSync objects for the TypeScript/JavaScript provider docs and
  maturation notes.
- Add claims for explicit-command TypeScript checks, structured repair facts,
  and advisory fixture evidence.
- Back those claims with explicit source/test evidence regions.
- Update public DocSync trace tests so future removal of provider-specific
  public docs coverage fails.
- Keep this documentation/test-only; no provider runtime behavior changes.

## Non-goals

- Do not add another ecosystem provider.
- Do not promote TypeScript/JavaScript to supported status.
- Do not add TypeScript/JavaScript blocking reviewability gates.
- Do not implement TypeScript starter files, package-manager autodetection, or
  coverage/security adapters.
- Do not change Python provider behavior.

## Acceptance Criteria

- `docs/typescript-javascript-provider.md` and
  `docs/case-studies/typescript-provider-maturation.md` are DocSync-traced.
- TypeScript provider claims point to implementation and test evidence, not only
  other prose.
- Public DocSync trace tests include provider-specific docs.
- `docsync check` passes.
- Normal precommit verification passes.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docsync/test_public_doc_trace.py tests/ecosystems/test_typescript_provider.py tests/context/test_typescript_exact_facts.py tests/core/test_typescript_structured_output.py tests/assess/test_typescript_reviewability_fixtures.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
