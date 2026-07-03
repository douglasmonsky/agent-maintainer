# Phase 131: TypeScript Real-Repo Reviewability Evidence

Status: complete

## Goal

Strengthen the TypeScript/JavaScript maturation track with end-to-end
reviewability evidence from real temporary Git repositories, not only patched
reader fixtures.

## Scope

- Add integration-style tests that create a temporary TypeScript repository,
  configure `[tool.agent_maintainer]`, commit a baseline, make realistic
  changes, and run `assess reviewability` through the public CLI.
- Cover at least one low-noise source-plus-test change and one source-heavy
  source-without-test change.
- Keep TypeScript/JavaScript findings advisory only.
- Keep Python-backed blocking reviewability gates unchanged.
- Update TypeScript maturation notes with the new evidence and remaining
  promotion gap.

## Non-goals

- Do not add new ecosystem providers.
- Do not add package-manager autodetection.
- Do not add TypeScript starter files.
- Do not add TypeScript blocking gates or active config thresholds.
- Do not change Python check names, commands, artifacts, profiles, or
  thresholds.

## Acceptance Criteria

- The test exercises the actual Git diff reader rather than monkeypatching
  changed-file data.
- The source-plus-test scenario produces TypeScript provider summaries without
  advisory source-without-test findings.
- The source-heavy source-only scenario produces TypeScript source-heavy and
  source-without-test advisory findings.
- The JSON payload remains compact and explicit enough to use as maturation
  evidence.
- Docs continue to state that TypeScript reviewability is advisory and not
  promotion-ready for blocking gates.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_typescript_real_repo_reviewability.py tests/assess/test_typescript_reviewability_fixtures.py tests/assess/test_reviewability_assessment.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
