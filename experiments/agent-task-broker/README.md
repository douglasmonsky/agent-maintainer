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
agent-task-broker lock claim task-0001 --kind path --target src/agent_maintainer/core/reporting.py --mode write
agent-task-broker locks
agent-task-broker handoff task-0001 --format markdown
agent-task-broker worktree plan task-0001 --format markdown
agent-task-broker result task-0001 --status done --summary "Done" \
  --verification "pytest tests/core/test_reporting.py -q" \
  --changed-file src/agent_maintainer/core/reporting.py
agent-task-broker lock release lock-0001
agent-task-broker give-up task-0002 --reason "needs-stronger-model"
```

State is stored under `.agent-task-broker/` in the target repository:

- `board.json` stores board metadata and task ids.
- `tasks/<id>.json` stores task state.
- `attempts/<id>-<n>.json` stores claim attempts.
- `results/<id>.json` stores structured done, blocked, escalate, or abandoned results.
- `locks/<id>.json` stores active read, write, or exclusive locks.
- `worktree-plans/<id>.json` stores suggested task worktree commands.

Agent-facing handoffs stay compact. The capsule includes the goal, allowed paths,
do-not-edit paths, constraints, evidence pointers, acceptance commands, give-up
rules, and result schema. Large logs and verifier artifacts should stay in Agent
Maintainer's own `.verify-logs/` artifacts, not in broker task text.

Locks are advisory but conflict-checked. Read locks can overlap; write and
exclusive locks conflict when exact paths, globs, package prefixes, docs, config,
or Tach policy targets overlap. Worktree planning is explicit: claiming a task or
lock does not create a worktree automatically.

## Adapter Contracts

Phase 161 defines broker-local adapter contracts before any automatic worker
spawning or external orchestration framework is enabled:

- `WorkerBackend` returns `WorkerRun` domain objects. The bundled
  `ManualWorkerBackend` only records a capsule or supplied structured result; it
  does not start Codex, Claude Code, OpenHands, or another agent.
- `CodexSdkWorkerBackend` is a plan-only adapter for the official Python Codex
  SDK path (`openai-codex`, `AsyncCodex`, `workspace_write`). It emits the
  request shape a future runner should execute, but it does not import the SDK,
  create threads, or spawn an agent.
- `WorkspaceBackend` returns `WorkspaceHandle` domain objects. The bundled
  `GitWorktreeWorkspaceBackend.plan(...)` only returns the worktree command;
  worktree creation requires calling `create(...)` explicitly.
- `WorkflowEngine` returns `WorkflowTransition` domain objects over local
  `BrokerStore` state. The bundled state machine selects, claims, and finishes
  tasks deterministically.
- `TraceSink` emits bounded local task-broker events. The bundled JSONL sink
  writes under `.agent-task-broker/traces/events.jsonl`.

Future framework backends should start disabled with explicit missing-dependency
diagnostics. Adapters must not decide verifier policy, merge safety, lock
policy, task acceptance, model tier, task risk, or escalation policy.
Worker execution should use official Codex SDK or Codex MCP plus Agents SDK
surfaces rather than a broker-owned agent polling loop.

## Model-Tier Routing

Phase 162 adds deterministic advisory routing before any worker backend can make
model or provider choices. `ModelRoutingPolicy` returns one of:

- `cheap-local-allowed`;
- `standard-worker-required`;
- `strong-worker-required`;
- `human-review-required`.

Cheap/local routing requires low difficulty, high confidence, bounded context,
explicit allowed paths, and focused verification. Failed verification,
low-confidence classification, repeated cheap-worker failure, oversized context,
ambiguous ownership, architecture/CI/security surfaces, and credential or
sensitive-data surfaces all escalate. Route decisions are advisory until
dogfood evidence proves low false-negative risk.
