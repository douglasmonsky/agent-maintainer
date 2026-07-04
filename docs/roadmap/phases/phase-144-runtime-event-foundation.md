# Phase 144: Runtime Event Foundation

Status: complete

## Goal

Implement the first local structured runtime event foundation so Agent
Maintainer can observe its own dogfooding quality without expanding normal
agent-facing verifier output.

## Scope

- Add configuration fields for local runtime events, disabled by default for
  downstream users.
- Add a small internal runtime event model with stable event names, severity,
  timestamps, correlation fields, and JSON-serializable attributes.
- Add a safe JSONL writer with deterministic local retention.
- Add redaction helpers for exception messages and event attributes.
- Add in-memory sink support for tests.
- Add event-contract tests for schema shape, retention, redaction, and
  crash-safe write degradation.
- Enable this repository to dogfood the foundation only after local tests prove
  the event writer is quiet and bounded.

## Non-goals

- No OpenTelemetry exporter.
- No `structlog` dependency.
- No remote log shipping.
- No raw stdout, stderr, tracebacks, prompts, file contents, or environment
  dumps in event records.
- No broad instrumentation of every verifier boundary in the first commit.
- No downstream blocking gate based on runtime events.

## Deliverables

- Runtime event config fields in `[tool.agent_maintainer]`.
- `src/agent_maintainer/runtime_events/` foundation modules.
- Tests for event serialization, redaction, retention, and no-op degradation.
- Repository config dogfooding the local event writer with bounded retention.
- Documentation updates explaining that OpenTelemetry remains a later optional
  exporter path.

## Acceptance Criteria

- Event records are compact JSONL objects with schema version, event name,
  timestamp, severity, command/profile/check/hook correlation where provided,
  status/duration fields where relevant, and small sanitized attributes.
- Event writer failures do not mask the original Agent Maintainer operation.
- Retention keeps the newest event files deterministically.
- Tests prove secrets and raw transcripts are not written directly into events.
- Normal verifier summaries remain unchanged.
- The implementation keeps the Phase 142 stance: local events first, optional
  OpenTelemetry later.

## Verification

Run focused runtime-event tests, config metadata tests, docs checks, and the
normal precommit profile. Run broader verifier profiles before merge.

## Follow-up

Future phases should instrument command/profile/check/hook/artifact boundaries,
then add a compact dogfood quality report once enough event data exists to make
the report useful.
