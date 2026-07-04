# 2026-07-04: Repair-Fact Coverage Assessment Boundary

## Status

Accepted

## Context

Phase 147 adds an advisory assessment that measures whether recent verifier
failures produced structured repair facts or forced agents to expand raw logs.
The command reads run-scoped verifier manifests and known repair-fact parsers,
then ranks parser gaps by recent fallback failures and log size.

## Decision

Add repair-fact coverage modules under `agent_maintainer.assess`:

- `repair_fact_coverage` reads recent manifests and computes coverage.
- `repair_fact_coverage_models` owns typed report payloads.
- `repair_fact_coverage_reporting` renders compact text and JSON.

`agent_maintainer.assess.cli` may route the new
`assess repair-fact-coverage` subcommand. The assessment may depend on
`agent_context.failures` and existing context-pack exact-fact extraction, but it
must remain read-only and advisory.

## Why Not Architecture Drift

This is assessment/reporting over existing diagnostic artifacts, not a new
verifier gate. Keeping the command under `assess` avoids making context packs
own scorekeeping while reusing the same exact-fact extraction that agents
already consume. The command preserves summary-first output and keeps raw logs
on disk.

## Alternatives Considered

- Add this to `context failures`. Rejected because context commands retrieve
  evidence for a known failure, while this feature ranks parser gaps across
  recent runs.
- Add this to `report`. Rejected because static HTML reporting is a reader
  artifact, while Phase 147 needs an operational CLI signal for future agents.
- Add a blocking verifier check. Rejected because repair-fact coverage is still
  advisory and should not block normal development until parser maturity is
  better understood.

## Still Forbidden

- Do not paste raw logs into assessment output.
- Do not make this score a blocking verifier gate in this phase.
- Do not make context-pack modules depend on assessment modules.
