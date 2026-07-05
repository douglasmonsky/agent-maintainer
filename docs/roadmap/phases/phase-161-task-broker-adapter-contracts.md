# Phase 161: Task Broker Adapter Contracts

Status: planned

## Goal

Define task-broker worker, workspace, workflow, and trace contracts before adding
automatic agent spawning or external orchestration frameworks.

## Primary ROI

Cost medium, quality high, speed high: adapter contracts prevent framework
lock-in while preserving a path to Codex, Claude Code, OpenHands, OpenAI Agents
SDK, LangGraph, and observability backends.

## Scope

- Document and implement minimal task-broker contract models for:
  - `WorkerBackend`;
  - `WorkspaceBackend`;
  - `WorkflowEngine`;
  - task-broker `TraceSink` integration if Phase 158 has landed.
- Keep initial implementations local and deterministic:
  - manual/local worker result handling;
  - Git worktree workspace backend;
  - local state-machine workflow backend.
- Add conformance tests proving adapters return task-broker domain objects and do
  not leak framework-specific types.
- Add missing-dependency and disabled-backend diagnostics for optional future
  backends.
- Update task-broker docs to state no automatic spawning occurs until a backend
  is explicitly enabled.
- Preserve a future `ModelRoutingPolicy` seam, but do not implement routing
  decisions until Phase 162.

## Non-Goals

- Do not add LangGraph, AutoGen, CrewAI, OpenHands, OpenAI Agents SDK, Prefect,
  Temporal, Phoenix, Langfuse, DSPy, or A2A dependencies.
- Do not implement automatic Codex/Claude spawning in this phase.
- Do not move the task-broker incubator into core Agent Maintainer.
- Do not let adapters decide verifier policy, merge safety, lock policy, task
  acceptance, model tier, task risk, or escalation policy.

## Verification Acceptance Criteria

- Contract tests cover worker, workspace, workflow, and trace adapter shapes.
- Git worktree backend behavior remains explicit and opt-in.
- Task-broker downstream install contract still passes.
- No new non-core framework dependency appears in Agent Maintainer core extras.
- Contracts make it possible for Phase 162 to select among worker tiers without
  leaking provider-specific model APIs into task-broker policy.
- `python3 -m agent_maintainer verify --profile fast`
- `tach check --exact`

## Notes For Future Tasks

Use `docs/roadmap/agent-orchestration-adapter-doctrine.md` as the architecture
authority. If an external framework makes an existing task-broker contract harder
to express, stop and revise the adapter contract rather than weakening the
product boundary.

