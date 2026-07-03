# Phase 140: TypeScript Node Boilerplate External Comparison

Status: complete

## Goal

Broaden TypeScript reviewability evidence with a second public repository
comparison that includes a Node TypeScript boilerplate migration from Jest to
Vitest.

## Scope

- Record bounded `assess reviewability --json` output from a public Node
  TypeScript boilerplate commit.
- Cover source, tests, config, docs, and lockfile/dependency changes in one
  external comparison.
- Update TypeScript maturation notes without changing provider behavior.
- Keep the provider experimental and advisory-only.

## Non-goals

- No package-manager autodetection.
- No test-runner default inference.
- No command execution for npm, Jest, or Vitest.
- No external source-code vendoring.
- No blocking TypeScript reviewability gate.
- No provider promotion.

## Acceptance Criteria

- The fixture records repository URL, base commit, head commit, temporary
  config, command shape, and advisory reviewability JSON.
- Tests prove the recorded comparison has zero advisory findings.
- Tests prove the recorded comparison includes TypeScript source, test, and
  dependency classifications plus global config/docs classifications.
- TypeScript maturation notes describe the second comparison and keep broader
  external samples as a remaining promotion requirement.
- DocSync trace links the public claim to the updated fixture tests.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_typescript_external_reviewability_fixture.py tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
