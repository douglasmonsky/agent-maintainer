# Phase 159: Scoring Dataset Optimization Prep

Status: planned

## Goal

Collect labeled examples for future deterministic, LLM, or DSPy-style scoring without introducing optimization frameworks yet.

## Primary ROI

Cost medium, quality medium, speed medium: future classifiers need examples before models.

## Scope

- Create `src/agent_maintainer/scoring/` with dataset and CLI modules.
- Add `scoring examples add`, `list`, and `export --format jsonl`.
- Write `.verify-logs/scoring/examples.jsonl`.
- Validate schema on write.
- No model calls, external optimizer, or non-JSONL storage.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `tests/scoring/test_scoring_dataset.py`
- `python3 -m agent_maintainer scoring examples list`
- Schema validation tests
- `python3 -m agent_maintainer verify --profile fast`
- `tach check --exact`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 159. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
