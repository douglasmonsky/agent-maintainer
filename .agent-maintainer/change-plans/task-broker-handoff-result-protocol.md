+++
id = "task-broker-handoff-result-protocol"
kind = "feature"
status = "active"
base_ref = "origin/main"
expires = 2026-07-19
allowed_paths = [
  "experiments/agent-task-broker/**",
  "docs/ROADMAP.md",
  "docs/roadmap/phases/phase-153-task-broker-handoff-result-protocol.md",
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

# Cohesive Change Plan: task-broker-handoff-result-protocol

## Why this change intentionally large

Phase 153 adds the first task handoff contract to the downstream broker
experiment. The handoff command, result validation, CLI wiring, and
experiment-local tests need to land together so subagent task capsules and
structured outcomes are testable as one protocol.

## Why this should not be split smaller

Handoff output without result validation would not enforce completion quality.
Result validation without handoff schema would lack the capsule contract. The
tests need both sides to prevent drift between what agents receive and what they
must return.

## What allowed to change

- `experiments/agent-task-broker/` handoff/result protocol modules and tests.
- Experiment README command examples if needed.
- Roadmap Phase 153 status files.
- Active change-plan cleanup from completed Phase 152.

## What must not change

- Agent Maintainer runtime behavior.
- Core package imports from `agent_task_broker`.
- Verifier profiles, hooks, generated guidance, or package metadata.

## Verification plan

- `experiments/agent-task-broker/tests/test_handoff.py`.
- `experiments/agent-task-broker/tests/test_results.py`.
- `agent-task-broker handoff task-0001 --format json`.
- `agent-task-broker give-up task-0001 --reason needs-stronger-model`.
- `python3 -m agent_maintainer verify --profile fast`.

## Rollback plan

Remove the handoff/result protocol modules, CLI command, tests, and Phase 153
status updates. The Phase 152 board/task storage remains valid.

## Follow-up ratchet work

Phase 154 should add lock and worktree planning only after this protocol proves
task capsules and result statuses stay compact and deterministic.
