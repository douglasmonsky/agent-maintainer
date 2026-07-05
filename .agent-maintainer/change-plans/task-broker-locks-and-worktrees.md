+++
id = "task-broker-locks-and-worktrees"
kind = "feature"
status = "active"
base_ref = "origin/main"
expires = 2026-07-19
allowed_paths = [
  "experiments/agent-task-broker/**",
  "docs/ROADMAP.md",
  "docs/roadmap/phases/phase-154-task-broker-locks-and-worktrees.md",
  ".agent-maintainer/change-plans/**",
]
forbidden_paths = ["src/agent_maintainer/**", "src/agent_context/**", ".env", ".env.*"]
max_changed_files = 30
max_changed_lines = 3000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: task-broker-locks-and-worktrees

## Why this change intentionally large

Phase 154 adds task-broker lock conflict detection and worktree planning inside the downstream experiment. The lock model, CLI wiring, store persistence, worktree planning, README examples, and focused tests need to land together so parallel-agent coordination is usable and testable.

## Why this should not be split smaller

Locks without CLI commands are not dogfoodable. Worktree planning without task-scoped locks does not prevent agent collisions. Tests need both pieces so the experiment proves scoped handoff, locking, and isolation planning as one workflow.

## What allowed to change

- `experiments/agent-task-broker/` lock, worktree, CLI, store, README, and tests.
- Roadmap Phase 154 status files.
- Active change-plan cleanup.

## What must not change

- Agent Maintainer runtime behavior.
- Core package imports from `agent_task_broker`.
- Generated guidance or verifier semantics.
- External plugin/provider APIs.

## Verification plan

- Focused task-broker lock/worktree tests.
- Downstream broker contract proxy test.
- Ruff check and format check for experiment files.
- `just change-plan-check`.
- `tach check --exact`.
- DocSync doctor and check.
- `just vp`.
- `just v`.

## Rollback plan

Revert the Phase 154 commit. The broker experiment will keep Phase 153 handoff and result behavior without lock or worktree planning commands.

## Follow-up ratchet work

If the broker incubator proves useful, add stronger downstream integration checks for real Git worktree creation and lock lifecycle cleanup after task completion.
