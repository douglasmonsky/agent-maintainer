# 2026-07-06: Agent efficacy assessment boundary

## Status

Accepted.

## Context

Phase 164 needs a local report that shows whether agent-facing primitives reduce
duplicate verifier work, repair-loop churn, context expansion waste, and wait
helper uncertainty. The evidence already exists in local runtime-event JSONL
files and verifier manifests; adding a remote telemetry layer would violate the
privacy-preserving product stance.

## Decision

Add `agent_maintainer.assess.efficacy` as the local builder for advisory agent
efficacy metrics. It may read compact runtime-event records and verifier
manifest metadata, but it must not ingest raw chat transcripts, raw check logs,
provider billing data, or network telemetry. Keep payload models in
`efficacy_models` and text rendering in `efficacy_reporting` so the assessment
builder stays focused.

## Consequences

`assess efficacy` reports measured metrics where events support them and labels
proxy values as estimates. Unknown metrics remain visible instead of silently
pretending manual escalation or true provider-token savings are measured.

## What remains forbidden?

The efficacy assessment must stay advisory, local, and artifact-backed. It must
not become a verifier gate, upload telemetry, read private prompt text, or infer
provider cost from secrets or account data.

## Review or expiration condition

Revisit after runtime events add explicit manual-escalation and context-pointer
open events; those should replace the current proxy calculations.
