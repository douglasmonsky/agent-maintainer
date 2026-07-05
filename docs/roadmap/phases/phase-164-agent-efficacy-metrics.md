# Phase 164: Agent Efficacy Metrics

Status: planned

## Goal

Measure whether Agent Maintainer actually reduces token use, duplicate work, and
repair-loop thrash while preserving or improving output quality.

## Scope

- Define local efficacy metrics for agent-facing primitives:
  - token reduction from repair capsules and compact hook output;
  - pointer follow-through rate for context packs and run-scoped artifacts;
  - context-pack expansion rate after pointer output;
  - duplicate verifier/profile avoidance;
  - repair-capsule next-action success rate;
  - time from first failure to passing rerun;
  - repeated failed-command patterns;
  - manual escalation rate for ambiguous or high-risk tasks.
- Build metrics from existing runtime events, verifier manifests, hook events,
  context-pack artifacts, and wait/async readiness events.
- Keep metrics local, privacy-preserving, and artifact-backed.
- Add a compact command/report that summarizes cost, quality, and speed impact
  without dumping raw logs.
- Use metrics to assess whether guidance, hooks, MCP tools, wait helpers, and
  context pointers improve future calls.

## Non-Goals

- Do not upload telemetry.
- Do not add model-provider billing integration.
- Do not make efficacy score a blocking gate initially.
- Do not require agents to manually annotate every action.

## Acceptance Criteria

- Efficacy report includes token/context savings proxies, duplicate-run
  avoidance, pointer usage, and repair-loop outcome metrics.
- Runtime events capture enough data to compute the report without raw chat
  transcript ingestion.
- Report clearly distinguishes measured data from estimates.
- Docs explain how to interpret the metrics and what actions should follow.
- Dogfood run records baseline before turning any metric into a ratchet.

## Notes

This phase should answer whether recent product work is paying rent: compact
repair capsules, context pointers, wait helpers, async rewake, MCP tools, and
guidance changes should reduce tokens and repeated work. If they do not, the
metrics should make that visible before more automation is added.
