# Phase 160: ROI Loop Dogfood Case Study

Status: planned

## Goal

Prove the Future-Call ROI loop improves cost, quality, and speed on at least one
real Agent Maintainer dogfood task.

## Primary ROI

Cost medium, quality high, speed medium: the track needs measured proof, not just
infrastructure.

## Scope

- Create `docs/case-studies/future-call-roi-loop.md`.
- Update the case-study index and DocSync trace when relevant.
- Include baseline workflow, new workflow, cost impact, quality impact, speed
  impact, evidence, and remaining gaps.
- Use real measured evidence where available; state unavailable metrics
  explicitly.
- Include whether the evidence supports later model-tier routing for cheaper
  workers on easy tasks, or whether more labeled examples are needed.
- Evaluate whether task-broker, MCP, context, runtime-event, and adapter doctrine
  primitives reduce token waste, conflict risk, and verification thrash before
  any external orchestration framework is adopted.
- Do not invent numbers.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make this phase
  pass.
- Do not claim cheap-worker routing is safe without measured verification and
  escalation evidence.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event
  contract completion.

## Verification Acceptance Criteria

- `tests/docs/test_future_call_roi_case_study.py`
- `docsync check`
- `python3 -m agent_maintainer verify --profile precommit`
- `tach check --exact`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 160. Keep the PR
scoped to this phase unless the user explicitly asks to bundle phases.
