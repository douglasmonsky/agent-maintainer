# Phase 152: Agent Task Broker Incubator Scaffold

Status: complete

## Goal

Create a hermetic downstream task-broker experiment that consumes Agent Maintainer like an installed package.

## Primary ROI

Cost high, quality medium-high, speed high: task brokering should be tested downstream before entering core.

## Scope

- Create `experiments/agent-task-broker/` with its own `pyproject.toml`, source tree, README, and tests.
- Package name is `agent-task-broker`; it depends on `agent-maintainer>=0.1.0b5`.
- Add commands for init, add, list, next, claim, complete, and give-up.
- Store state under `.agent-task-broker/` with board, task, attempt, and result files.
- Main repo must not import `agent_task_broker`; add architecture test for that boundary.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- Build Agent Maintainer wheel and install it into a clean venv
- Install the experiment editable inside that venv
- `experiments/agent-task-broker/tests/test_downstream_install_contract.py`
- `tests/architecture/test_experiment_boundaries.py`
- `python3 -m agent_maintainer verify --profile fast`
- `tach check --exact`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 152. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
