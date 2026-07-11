<!-- docsync:object docs.future_call_roi_acceleration.overview -->

# Future-Call ROI Acceleration Roadmap

This roadmap prioritizes Agent Maintainer work by expected impact on future
agent calls. The scoring dimensions are:

- Cost: fewer tokens, fewer redundant tool calls, cheaper model routing, less
  noisy context, fewer repeated validations.
- Quality: fewer regressions, clearer repair facts, tighter docs freshness,
  safer architecture boundaries, lower chance of agent thrash.
- Speed: faster next action selection, less manual triage, quicker handoffs,
  shorter verification loops, better recovery after compaction.

The immediate strategy is:

```text
runtime events + repair facts + DocSync + context packs + file baselines + package-boundary tests
  -> local scores and attention signals
  -> better next actions
  -> smaller handoffs
  -> safer task routing
  -> faster, cheaper, higher-quality future agent work
```

## Invariants

- Agent Maintainer remains the verifier, context, DocSync, guidance, and policy
  substrate.
- The task broker is a downstream incubator and must consume Agent Maintainer
  through installed public package imports, CLI commands, and artifacts.
- No extracted internal package may import `agent_maintainer`.
- No phase may widen Tach buckets to silence architecture failures.
- Every new summary preserves raw evidence handles.
- DocSync confines bounded inputs to the repository and writes verifier reports
  only when the integration requests them explicitly.
- Every agent-facing output prefers compact repair capsules and expansion
  commands over pasted logs.
- Any external orchestration framework sits behind an adapter and must not own
  Agent Maintainer policy.
- Agent orchestration follows
  [`Agent Orchestration Adapter Doctrine`](agent-orchestration-adapter-doctrine.md):
  domain contracts first, adapters second, external frameworks third.
- Phase 145 is a completed prerequisite for Phase 146 behavior work.

## ROI Order

| Order | Phase | Main return |
| ---: | --- | --- |
| 1 | Runtime event intelligence | Future agents see what ran, failed, and cost time. |
| 2 | Repair-fact coverage | Weak parser gaps become visible and rankable. |
| 3 | Surgical context expansion | Agents inspect the smallest useful evidence first. |
| 4 | DocSync verifier integration | Documentation freshness enters the repair loop. |
| 5 | Attention ledger | High-risk, high-value files become visible. |
| 6 | Attention-weighted context packs | High-risk files get better context automatically. |
| 7 | Task broker incubator | Future work becomes scoped, claimable, and reusable. |
| 8 | Handoff/result protocol | Subagents work from small task capsules. |
| 9 | Locks/worktrees | Parallel agents stop colliding. |
| 10 | Claude async rewake | Slow validation no longer wastes agent turns. |
| 11 | MCP surface | Agents access stable tools through schemas instead of shell guessing. |
| 12 | Recall/compaction ledger | Long work survives context loss. |
| 13 | Observability export | Local traces can flow to external observability later. |
| 14 | Scoring dataset | Future classifiers get labeled examples. |
| 15 | Dogfood case study | The loop proves cost, quality, and speed impact. |
| 16 | Task broker adapter contracts | External frameworks stay replaceable before spawning begins. |
| 17 | Model-tier routing policy | Easier tasks can use cheaper workers with escalation on uncertainty. |

<!-- docsync:object.end docs.future_call_roi_acceleration.overview -->

## Phase Index

Priority-one interrupt before Phase 148:

[`Agent Cadence Waste Hardening`](priority-one-agent-cadence-waste-hardening.md).

| Phase | Link |
| ---: | --- |
| 145 | [Runtime Event Contract Expansion](phases/phase-145-runtime-event-contract-expansion.md) |
| 146 | [Runtime Event Intelligence Summary CLI](phases/phase-146-runtime-event-intelligence-summary.md) |
| 147 | [Repair-Fact Coverage Score](phases/phase-147-repair-fact-coverage-score.md) |
| 148 | [Surgical Context Expansion Ranking](phases/phase-148-surgical-context-expansion-ranking.md) |
| 149 | [DocSync Verifier Integration Repair Facts](phases/phase-149-docsync-verifier-integration.md) |
| 150 | [Attention Ledger v0](phases/phase-150-attention-ledger-v0.md) |
| 151 | [Attention-Weighted Context Packs](phases/phase-151-attention-weighted-context-packs.md) |
| 152 | [Agent Task Broker Incubator Scaffold](phases/phase-152-agent-task-broker-incubator.md) |
| 153 | [Task Broker Handoff Result Protocol](phases/phase-153-task-broker-handoff-result-protocol.md) |
| 154 | [Task Broker Locks And Worktree Planning](phases/phase-154-task-broker-locks-and-worktrees.md) |
| 155 | [Claude Async Rewake Hook Option](phases/phase-155-claude-async-rewake-hook-option.md) |
| 156 | [Agent Maintainer MCP Surface v0](phases/phase-156-agent-maintainer-mcp-surface-v0.md) |
| 157 | [Context Recall Compaction Ledger v0](phases/phase-157-context-recall-compaction-ledger-v0.md) |
| 158 | [Local Observability Export Contract](phases/phase-158-local-observability-export-contract.md) |
| 159 | [Scoring Dataset Optimization Prep](phases/phase-159-scoring-dataset-optimization-prep.md) |
| 160 | [ROI Loop Dogfood Case Study](phases/phase-160-roi-loop-dogfood-case-study.md) |
| 161 | [Task Broker Adapter Contracts](phases/phase-161-task-broker-adapter-contracts.md) |
| 162 | [Task Broker Model-Tier Routing Policy](phases/phase-162-task-broker-model-tier-routing-policy.md) |

## Cross-Phase Dependency Order

Implement phases in this order unless the user explicitly instructs otherwise:

```text
145 Runtime Event Contract Expansion
146 Runtime Event Intelligence Summary CLI
147 Repair-Fact Coverage Score
148 Surgical Context Expansion Ranking
149 DocSync Verifier Integration Repair Facts
150 Attention Ledger v0
151 Attention-Weighted Context Packs
152 Agent Task Broker Incubator Scaffold
153 Task Broker Handoff Result Protocol
154 Task Broker Locks Worktree Planning
155 Claude Async Rewake Hook Option
156 Agent Maintainer MCP Surface v0
157 Context Recall Compaction Ledger v0
158 Local Observability Export Contract
159 Scoring Dataset Optimization Prep
160 ROI Loop Dogfood Case Study
161 Task Broker Adapter Contracts
162 Task Broker Model-Tier Routing Policy
```

## Framework Adoption Sequence

Use open-source frameworks for execution, communication, tracing, and workflow
plumbing, but keep Agent Maintainer's repo intelligence, verification policy,
context discipline, task-routing semantics, and lock rules in Agent Maintainer
domain contracts.

Move up:

- MCP as the first `ToolServerBackend` path.
- Local JSONL/OpenTelemetry-shaped runtime events as the first `TraceSink`.
- Worker, workspace, and workflow contracts before any automatic spawning.
- Git worktree-per-task as the default workspace isolation model.
- Model-tier routing after worker contracts exist: task difficulty, risk, and
  confidence decide when a cheaper worker is appropriate.

Keep later:

- LangGraph as an optional `WorkflowEngine` backend only after local lifecycle
  semantics are stable.
- OpenAI Agents SDK, Claude Code, Codex, and OpenHands as optional
  `WorkerBackend` implementations only after worker contracts exist.
- Phoenix, Langfuse, or OTLP exporters only after local trace schemas stabilize.
- DSPy scoring only after Phase 159 produces labeled examples.
- Model/router optimization only after cheap-worker routing has a deterministic
  policy and measured failure/escalation data.
- Prefect or Temporal only after local orchestration needs durable distributed
  execution.
- A2A only if external agent systems need to coordinate with Agent Maintainer.

Discard for now:

- Adding LangGraph, AutoGen, CrewAI, OpenHands, Prefect, Temporal, Langfuse,
  Phoenix, DSPy, or A2A directly to core Agent Maintainer.
- Letting framework adapters decide verifier policy, merge safety, task
  acceptance, lock policy, or repository risk.
- Adding framework dependencies to core installs.

## Global Implementation Rules

- Keep one phase per PR unless the user explicitly asks for bundled work.
- Each phase updates `docs/ROADMAP.md`, its phase file, and DocSync trace
  coverage when public or maintainer docs change materially.
- Run focused tests, `python3 -m agent_maintainer guidance --check`,
  `docsync doctor`, `docsync check`,
  `python3 -m agent_maintainer verify --profile fast`, and
  `tach check --exact` for each phase.
- Phases touching verifier profiles, context packs, hooks, or config also run
  `python3 -m agent_maintainer verify --profile precommit`.
- Phases touching packaging, experiments, MCP, or optional dependencies also run
  build/install checks.
- Never regress pointer-first context packs, run-scoped artifacts, extracted
  package dependency direction, DocSync package independence, Tach exactness,
  generated guidance freshness, quiet verifier output, or adapter boundaries.

## Backlog ROI Ledger

| Item | Cost ROI | Quality ROI | Speed ROI | Dependency |
| --- | ---: | ---: | ---: | --- |
| Runtime event summary | 5 | 4 | 5 | Runtime events |
| Repair-fact coverage | 5 | 5 | 5 | Repair facts |
| Surgical expansion | 5 | 4 | 5 | Context packs + facts |
| DocSync verifier integration | 4 | 5 | 4 | DocSync |
| Attention ledger | 5 | 5 | 4 | Events + DocSync + baselines |
| Attention-weighted packs | 5 | 5 | 5 | Attention ledger |
| Task broker scaffold | 5 | 4 | 5 | Public CLI/artifacts |
| Handoff/result protocol | 5 | 4 | 5 | Task broker scaffold |
| Locks/worktrees | 4 | 5 | 4 | Task broker protocol |
| Claude async rewake | 4 | 4 | 4 | Agent client hooks |
| MCP surface | 4 | 4 | 5 | Stable CLI/API |
| Recall ledger | 4 | 3 | 4 | Context commands |
| Observability export | 3 | 4 | 3 | Runtime events |
| Scoring dataset | 3 | 3 | 3 | Attention/task data |
| Dogfood case study | 3 | 5 | 3 | Most prior phases |
| Task broker adapter contracts | 4 | 5 | 4 | Task broker + observability |
| Model-tier routing | 5 | 4 | 5 | Adapter contracts + scoring data |

## Final Definition Done

Future-Call ROI Acceleration track is complete when runtime events can be
summarized locally, repair-fact coverage identifies weak checks, context packs
recommend surgical next actions, DocSync participates in verifier repair loops,
attention scores guide high-risk file context, the hermetic task broker can
create complete scoped tasks, Claude async rewake is opt-in, a minimal typed tool
surface exists, recall survives compaction, events export through a local
contract, scoring examples are recorded, the dogfood case study shows measurable
cost, quality, and speed impact, and task-broker worker/workspace/workflow
contracts are defined before any spawning backend is added. Model-tier routing
is then available so low-risk, low-complexity tasks can use cheaper workers while
uncertain, failing, risky, or policy-sensitive work escalates to stronger models.
