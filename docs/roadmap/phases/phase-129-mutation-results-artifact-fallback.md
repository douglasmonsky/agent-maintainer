# Phase 129: Mutation Results Artifact Fallback

Status: complete

## Goal

Keep `test-intel mutation-results` useful after successful Mutmut runs clean the
live `mutants/` directory.

## Scope

- Preserve live `mutants/mutmut-cicd-stats.json` as the first-priority source.
- Fall back to retained run-scoped Mutmut stats/log artifacts.
- Fall back to retained advisory mutation-sweep stats artifacts when live stats
  and run artifacts are absent.
- Report the source path so users can tell whether results came from live
  `mutants/` or retained diagnostics.

## Non-goals

- Do not preserve `mutants/` by default.
- Do not make advisory sweep survivor counts blocking.
- Do not change Mutmut runner cleanup behavior.
- Do not add new mutation targets.

## Acceptance Criteria

- `python -m agent_maintainer test-intel mutation-results` succeeds when a
  retained mutation stats artifact exists and live `mutants/` stats are absent.
- JSON output includes source kind and path.
- Missing stats still fail compactly.
- Focused mutation-results tests pass.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/test_intel/test_mutation_results_cli.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer test-intel mutation-results
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
