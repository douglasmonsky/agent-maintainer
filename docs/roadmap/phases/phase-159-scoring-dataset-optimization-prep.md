# Phase 159: Scoring Dataset Optimization Prep

Status: planned

## Goal

Collect labeled examples for future deterministic, LLM, and DSPy-style scoring
without introducing optimization frameworks yet.

## Primary ROI

Cost medium, quality medium, speed medium: future classifiers and model-tier
routing need examples before models.

## Scope

- Create `src/agent_maintainer/scoring/` dataset CLI modules.
- Add `scoring examples add`, `list`, and `export --format jsonl`.
- Write `.verify-logs/scoring/examples.jsonl`.
- Validate schema on write.
- Include labels useful to future model-tier routing:
  - task difficulty;
  - risk surface;
  - context size;
  - verification outcome;
  - whether a cheap worker would have been acceptable;
  - whether escalation was required and why.
- No model calls, external optimizer, or non-JSONL storage.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make this phase
  pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event
  contract completion.

## Verification Acceptance Criteria

- `tests/scoring/test_scoring_dataset.py`
- `python3 -m agent_maintainer scoring examples list`
- Schema validation tests cover route-relevant labels without provider-specific
  model names.
- `python3 -m agent_maintainer verify --profile fast`
- `tach check --exact`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 159. Keep the PR
scoped to this phase unless the user explicitly asks to bundle phases.
