# Phase 160: ROI Loop Dogfood Case Study

Status: planned

## Goal

Prove the Future-Call ROI loop improves cost, quality, and speed on at least one real Agent Maintainer dogfood task.

## Primary ROI

Cost medium, quality high, speed medium: the track needs measured proof, not just infrastructure.

## Scope

- Create `docs/case-studies/future-call-roi-loop.md`.
- Update case-study index and DocSync trace.
- Include baseline workflow, new workflow, cost impact, quality impact, speed impact, evidence, and remaining gaps.
- Use real measured evidence where available; state unavailable metrics explicitly.
- Do not invent numbers.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `tests/docs/test_future_call_roi_case_study.py`
- `docsync check`
- `python3 -m agent_maintainer verify --profile precommit`
- `tach check --exact`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 160. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
