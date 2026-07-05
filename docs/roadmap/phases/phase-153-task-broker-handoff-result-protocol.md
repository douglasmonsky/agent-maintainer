# Phase 153: Task Broker Handoff Result Protocol

Status: complete

## Goal

Give subagents compact task capsules and require structured done, blocked, escalate, or abandoned results.

## Primary ROI

Cost high, quality medium-high, speed high: subagents need small scopes and structured outcomes.

## Scope

- Add handoff and result modules inside the task-broker experiment.
- Add `agent-task-broker handoff <task>` with Markdown and JSON output.
- Handoff must include goal, allowed paths, do-not-edit paths, constraints, evidence, acceptance commands, give-up rules, and result schema.
- Validate result statuses: done requires verification, blocked requires needs, escalate requires reason.
- Normalize changed file paths as repo-relative.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `experiments/agent-task-broker/tests/test_handoff.py`
- `experiments/agent-task-broker/tests/test_results.py`
- `agent-task-broker handoff task-001 --format json`
- `agent-task-broker give-up task-001 --reason needs-stronger-model`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 153. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
