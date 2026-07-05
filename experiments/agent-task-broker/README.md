# Agent Task Broker Incubator

This package is a downstream experiment for scoped agent task handoffs. It is
intentionally outside the core Agent Maintainer package and consumes Agent
Maintainer as an installed dependency.

The incubator is not a public plugin API. Its purpose is to test task-broker
workflow ideas before any behavior moves into Agent Maintainer.

## Commands

```bash
agent-task-broker init
agent-task-broker add "Split reporting helpers"
agent-task-broker list
agent-task-broker next
agent-task-broker claim task-0001 --agent codex
agent-task-broker complete task-0001 --summary "Done"
agent-task-broker give-up task-0002 --reason "blocked on credentials"
```

State is stored under `.agent-task-broker/` in the target repository:

- `board.json` stores board metadata and task ids.
- `tasks/<id>.json` stores task state.
- `attempts/<id>-<n>.json` stores claim attempts.
- `results/<id>.json` stores completion or give-up results.

Agent-facing output stays compact. Large logs and verifier artifacts should stay
in Agent Maintainer's own `.verify-logs/` artifacts, not in broker task text.
