+++
id = "agent-task-broker-incubator"
kind = "feature"
status = "active"
base_ref = "origin/main"
expires = 2026-07-19
allowed_paths = [
  "experiments/agent-task-broker/**",
  "tests/architecture/**",
  "tests/packaging/**",
  "docs/ROADMAP.md",
  "docs/roadmap/phases/phase-152-agent-task-broker-incubator.md",
  "pyproject.toml",
  ".agent-maintainer/change-plans/**",
]
forbidden_paths = ["src/agent_maintainer/**", "src/agent_context/**", ".env", ".env.*"]
max_changed_files = 40
max_changed_lines = 4000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: agent-task-broker-incubator

## Why this change intentionally large

Phase 152 creates a hermetic downstream experiment package rather than a core
Agent Maintainer feature. The change needs package metadata, CLI/storage code,
experiment-local tests, and one main-repo architecture boundary test together to
prove the incubator can consume Agent Maintainer as an installed dependency
without becoming part of the core package.

## Why this should not be split smaller

A package scaffold without install tests would not prove the downstream contract.
Install tests without a minimal CLI would not exercise the package. The boundary
test belongs in the same phase because it prevents accidental core coupling from
the first incubator commit.

## What allowed to change

- `experiments/agent-task-broker/` package, docs, tests.
- Main-repo architecture test proving core code does not import the experiment.
- Roadmap Phase 152 status files.
- Root Deptry first-party metadata required because full verification scans the
  experiment package source.

## What must not change

- Agent Maintainer runtime behavior.
- Verifier profiles, generated guidance, hooks, or package metadata.
- Core package imports from `agent_task_broker`.

## Verification plan

- `experiments/agent-task-broker/tests/test_downstream_install_contract.py`.
- `tests/architecture/test_experiment_boundaries.py`.
- `tach check --exact`.
- `python3 -m agent_maintainer verify --profile fast`.

## Rollback plan

Remove the experiment package, boundary test, and roadmap Phase 152 status
updates. No persisted Agent Maintainer user config or runtime behavior changes.

## Follow-up ratchet work

Phase 153 should define the handoff/result protocol after this package scaffold
proves a downstream incubator can install and run without core imports. Do not
promote task-broker behavior into Agent Maintainer until later phases prove the
protocol, locks, and worktree planning are low-noise.
