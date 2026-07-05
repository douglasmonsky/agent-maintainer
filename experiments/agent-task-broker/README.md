# Agent Task Broker Incubator

This package is a downstream experiment for scoped agent task handoffs. It is
intentionally outside the core Agent Maintainer package and consumes Agent
Maintainer as an installed dependency.

The incubator is not a public plugin API. Its purpose is to test task-broker
workflow ideas before any behavior moves into Agent Maintainer.

## Commands

```bash
agent-task-broker init
agent-task-broker add "Split reporting helpers" \
  --allowed-path src/agent_maintainer/core/reporting.py \
  --do-not-edit-path pyproject.toml \
  --constraint "Use apply_patch for manual edits." \
  --evidence ".verify-logs/runs/<run-id>/summary.md" \
  --acceptance-command "pytest tests/core/test_reporting.py -q"
agent-task-broker list
agent-task-broker next
agent-task-broker claim task-0001 --agent codex
agent-task-broker handoff task-0001 --format markdown
agent-task-broker result task-0001 --status done --summary "Done" \
  --verification "pytest tests/core/test_reporting.py -q" \
  --changed-file src/agent_maintainer/core/reporting.py
agent-task-broker give-up task-0002 --reason "needs-stronger-model"
```

State is stored under `.agent-task-broker/` in the target repository:

- `board.json` stores board metadata and task ids.
- `tasks/<id>.json` stores task state.
- `attempts/<id>-<n>.json` stores claim attempts.
- `results/<id>.json` stores structured done, blocked, escalate, or abandoned results.

Agent-facing handoffs stay compact. The capsule includes the goal, allowed paths,
do-not-edit paths, constraints, evidence pointers, acceptance commands, give-up
rules, and result schema. Large logs and verifier artifacts should stay in Agent
Maintainer's own `.verify-logs/` artifacts, not in broker task text.
