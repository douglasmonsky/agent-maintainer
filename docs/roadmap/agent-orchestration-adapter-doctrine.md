# Agent Orchestration Adapter Doctrine

Agent Maintainer should use strong open-source agent tools as replaceable
accelerators, not as the product boundary. The durable product boundary is the
repo-maintenance contract: verification policy, repair facts, context discipline,
task routing semantics, locks, worktrees, and evidence-backed handoffs.

## Decision

Use domain contracts first, adapters second, and external frameworks third.

This means Agent Maintainer and the task-broker incubator must not become "a
LangGraph app", "an AutoGen app", "a CrewAI app", or any other framework-shaped
product. Those tools may become backends after the local contracts prove useful.

## Current Assessment

Phases 152 through 154 are directionally correct and do not need to be reworked:

- Phase 152 created a downstream task-broker incubator rather than putting task
  brokering directly into core Agent Maintainer.
- Phase 153 added compact handoff and structured result contracts before any
  automatic spawning.
- Phase 154 added advisory locks and explicit worktree planning before parallel
  agents can collide.

The missing piece is an explicit adapter doctrine before future work adds MCP,
OpenAI Agents SDK, Claude/Codex worker integrations, OpenHands, LangGraph,
AutoGen, CrewAI, Prefect, Temporal, Phoenix, Langfuse, or DSPy.

## First-Class Contracts

Future implementation should introduce small contracts only when the next phase
needs them:

- `ToolServerBackend`: expose Agent Maintainer tools through CLI first, then MCP.
- `TraceSink`: write local JSONL/OpenTelemetry-shaped events first, then optional
  Phoenix/Langfuse/OTLP exporters.
- `WorkerBackend`: run one task capsule in one workspace and return a structured
  result without mutating broker state.
- `WorkspaceBackend`: create, inspect, diff, and clean task workspaces; Git
  worktrees are the default backend.
- `WorkflowEngine`: orchestrate task lifecycle; a local deterministic state
  machine comes before LangGraph.
- `ScoringBackend`: deterministic heuristics first, DSPy/LLM scorers only after
  labeled examples exist.
- `ModelRoutingPolicy`: choose a worker/model tier from task difficulty, risk,
  confidence, budget, and verification history. Start deterministic; optimize
  only after measured outcomes exist.

External framework objects must not leak through these contracts. Adapters return
Agent Maintainer/task-broker domain objects.

## Priority Order

Move up:

1. MCP surface as the first `ToolServerBackend` path.
2. Local JSONL/OpenTelemetry-shaped runtime events as the first `TraceSink`.
3. Worker/workspace/workflow contracts before any automatic agent spawning.
4. Git worktree-per-task as the default workspace isolation model.
5. Model-tier routing after worker contracts exist so easy tasks can run on
   cheaper workers and escalate when confidence drops.

Keep later:

- LangGraph as an optional workflow backend after local lifecycle semantics are
  stable.
- OpenAI Agents SDK, Claude Code, Codex, and OpenHands as possible
  `WorkerBackend` implementations after worker contracts exist.
- Phoenix/Langfuse exporters after local trace schemas stabilize.
- DSPy scoring after the scoring dataset phase produces labeled examples.
- Model-tier optimization after deterministic routing has measured
  failure/escalation data.
- Prefect/Temporal after local orchestration needs durable distributed execution.
- A2A only if external agent systems need to coordinate with Agent Maintainer.

Discard for now:

- Adding LangGraph, AutoGen, CrewAI, OpenHands, Prefect, Temporal, Langfuse,
  Phoenix, DSPy, or A2A directly to core Agent Maintainer.
- Letting any adapter decide verifier policy, merge safety, task acceptance, or
  repository risk.
- Adding framework dependencies to core installs.

## Adapter Rules

1. Core code talks to protocols and domain objects, not vendor/framework classes.
2. Adapters live behind optional extras or downstream incubator packages.
3. Every adapter gets conformance tests against the contract it implements.
4. Every adapter has a kill switch and a missing-dependency diagnostic.
5. Frameworks may execute tasks; Agent Maintainer decides policy.
6. Handoffs stay compact and artifact-backed; raw logs stay out of agent context.
7. No automatic spawning until task result, lock, worktree, and verification
   contracts are stable.

## Roadmap Placement

This doctrine affects current and upcoming phases as follows:

- Phase 156 should implement the MCP surface as a tool-server boundary, not as a
  broad agent-orchestration framework.
- Phase 158 should treat local runtime events as the source of truth and make
  external observability exporters optional future adapters.
- A new follow-up phase should define task-broker worker/workspace/workflow
  contracts before adding any spawning backend.
- The ROI dogfood case study should measure whether these primitives reduce
  token waste, conflict risk, and verification thrash before any framework is
  adopted.
- Model-tier routing should be an explicit post-adapter-contract phase, not an
  implicit behavior inside a worker backend.
