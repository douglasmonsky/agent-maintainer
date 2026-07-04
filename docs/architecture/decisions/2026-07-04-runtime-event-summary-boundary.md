# 2026-07-04: Runtime Event Summary Boundary

## Status

Accepted

## Context

Phase 146 turns local runtime event JSONL files into compact summaries for
agents and humans. The runtime event package already owns event models,
redaction, sinks, and command/hook/verifier adapters. The summary command needs
to read the same local JSONL files without making verifier output noisier or
pulling report rendering into runtime event storage.

## Decision

Add three modules inside `agent_maintainer.runtime_events`:

- `read` reads local JSONL event files and counts malformed lines.
- `summary` converts records into deterministic compact summaries.
- `cli` exposes `python -m agent_maintainer events ...` subcommands.

The top-level `agent_maintainer.cli` may route to `runtime_events.cli`.
The runtime-events package may continue depending only on its own modules and
configuration schema for default event paths.

## Why Not Architecture Drift

Runtime event summaries are part of the runtime event ownership boundary, not
static HTML report rendering. Keeping the reader and summarizer beside the event
model prevents `report` from becoming a generic observability package and keeps
the event contract testable without pulling in verifier internals.

The command is read-only and summary-first. It does not alter verifier behavior,
does not emit raw JSONL into normal output, and does not introduce remote
telemetry dependencies.

## Alternatives Considered

- Put event summaries under `agent_maintainer.report`.
  Rejected because report rendering owns static diagnostic reports, while this
  command is an operational query over runtime event artifacts.
- Add OpenTelemetry or `structlog` now.
  Rejected because Phase 146 needs a stable local event contract before external
  export formats add configuration, privacy, and support surface.
- Parse event JSONL inside each future agent feature.
  Rejected because duplicated parsing would make malformed-line handling,
  ordering, and compact output inconsistent.
