# Runtime Event Export Boundary

## Status

Accepted.

## Context

Runtime events are already local JSONL artifacts. Phase 158 needs exportable
local observability payloads without selecting a hosted telemetry backend or
adding network side effects.

## Decision

Add `agent_maintainer.runtime_events.export` as a sibling runtime-events module
owned by the runtime-events package. The events CLI may depend on it to render
local JSONL and OpenTelemetry-shaped JSON payloads, while the exporter depends
only on the existing runtime-event reader contract.

## Consequences

Runtime-event export stays local, deterministic, and side-effect free. Future
Phoenix, Langfuse, OTLP, or task-broker adapters can consume the local contract
after the schema proves useful.

Alternatives considered:

- Export directly from `runtime_events.cli`. Rejected because export formatting
  is a durable contract separate from argument parsing.
- Add an external telemetry dependency now. Rejected because this phase only
  requires local contracts and explicitly excludes network exporters.
- Drop source file and line metadata. Rejected because local repair workflows
  need event provenance when diagnosing generated artifacts.
