# Phase 154: Task Broker Locks And Worktree Planning

Status: planned

## Goal

Prevent parallel agents from editing the same logical scope and prepare worktree-per-task isolation.

## Primary ROI

Cost medium-high, quality high, speed medium-high: parallelism needs conflict detection before automation.

## Scope

- Add lock and worktree modules inside the task-broker experiment.
- Support path, package, doc, config, and tach lock kinds with read, write, exclusive modes.
- Add commands for locks, claim, release, worktree plan, and worktree create.
- Implement exact path, glob, package, and mode conflict rules.
- `worktree create` may create a worktree but must not delete worktrees automatically.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `experiments/agent-task-broker/tests/test_locks.py`
- `experiments/agent-task-broker/tests/test_worktrees.py`
- `agent-task-broker locks`
- `agent-task-broker worktree plan task-001`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 154. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
