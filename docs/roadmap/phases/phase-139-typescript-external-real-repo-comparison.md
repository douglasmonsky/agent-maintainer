# Phase 139: TypeScript External Real-Repo Comparison

Status: complete

## Goal

Record one external public TypeScript/JavaScript repository comparison for
`assess reviewability` so TypeScript provider maturation is not based only on
synthetic fixture repositories.

## Scope

- Run advisory reviewability against a public TypeScript repository commit.
- Keep only bounded result metadata and the reviewability JSON fixture.
- Update TypeScript maturation notes with the comparison outcome.
- Link the comparison to DocSync evidence.
- Keep TypeScript reviewability advisory-only.

## Non-goals

- No package-manager autodetection.
- No package-manager command execution.
- No external code vendoring.
- No blocking TypeScript reviewability gate.
- No supported-status promotion.
- No new ecosystem.

## Acceptance Criteria

- A fixture records repository URL, base commit, head commit, temporary config,
  command shape, and advisory reviewability JSON.
- Tests prove the recorded external comparison has a TypeScript source/test
  change pair with no advisory findings.
- TypeScript maturation notes mention the external comparison and keep the
  promotion bar conservative.
- DocSync trace links the public claim to durable evidence.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_typescript_external_reviewability_fixture.py tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
