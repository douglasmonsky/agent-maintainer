# Runtime Telemetry And Dogfood Logging Roadmap

Agent Maintainer should be observable without becoming chatty. The product
goal is a quiet control plane in normal agent conversations, with enough
structured local runtime evidence to debug dogfooding quality, hook behavior,
check selection, slow verification runs, stale installs, artifact retention,
and provider maturity.

This roadmap intentionally separates operational telemetry from user-facing
verification summaries. Verification output should stay compact. Detailed
runtime facts should live in bounded local artifacts.

## Industry Baseline

The practical industry baseline for a Python CLI like Agent Maintainer is:

- Use standard Python logging conventions where possible, especially for
  library code that should not configure a global root logger.
- Emit structured events for machine analysis instead of relying on prose log
  parsing.
- Correlate related events with stable identifiers such as command id, run id,
  profile, check name, hook invocation id, and repository root.
- Keep severity levels meaningful: debug for development detail, info for
  expected lifecycle events, warning for recoverable risk, error for failed
  operations.
- Keep sensitive content out of logs by default. Record paths, check names,
  exit codes, durations, and artifact references instead of raw file contents,
  secrets, full command transcripts, or private user data.
- Retain logs locally with deterministic pruning. Do not create an unbounded
  token or disk leak.
- Treat OpenTelemetry as the interoperability model, not necessarily the first
  implementation dependency.

Useful reference points:

- [Python logging](https://docs.python.org/3/library/logging.html) and the
  [Python logging cookbook](https://docs.python.org/3/howto/logging-cookbook.html)
  remain the standard library baseline. The cookbook includes structured
  logging patterns using JSON-serializable event data.
- [OpenTelemetry Logs](https://opentelemetry.io/docs/specs/otel/logs/) defines
  the broader observability model for logs, correlation, and interoperability.
- The
  [OpenTelemetry Logs Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/)
  is stable and names the concepts Agent Maintainer should mirror locally:
  timestamp, observed timestamp, trace context, severity, body, resource,
  instrumentation scope, attributes, and event name.
- [structlog](https://www.structlog.org/en/stable/) is a mature Python
  structured logging library worth considering if context binding and processor
  pipelines become valuable enough to justify a dependency.

## Product Stance

Agent Maintainer should not start by adding a full observability stack.

The first implementation should use a tiny internal runtime event model plus
a local JSONL writer. That keeps the dependency footprint low, makes tests
straightforward, and avoids forcing downstream repositories into observability
infrastructure.

OpenTelemetry exporter support belongs later, likely behind an optional extra,
after local runtime events prove useful. `structlog` should also remain a later
choice unless the internal event writer starts recreating its processor/context
model poorly.

Recommended first design:

```json
{
  "schema_version": 1,
  "event_name": "check.finished",
  "timestamp": "2026-07-03T20:30:00.000000Z",
  "severity": "info",
  "run_id": "20260703T203000Z-full-abc123",
  "command": "verify",
  "profile": "full",
  "check": "pyright",
  "duration_ms": 8421,
  "status": "pass",
  "exit_code": 0,
  "repo_configured": true,
  "sensitive": false,
  "attributes": {
    "artifact": ".verify-logs/runs/20260703T203000Z-full-abc123/pyright.log"
  }
}
```

The schema should be intentionally small. If an event needs raw stdout,
tracebacks, command output, or large diagnostics, it should point at existing
run-scoped artifacts instead of duplicating them.

## Config Shape

Proposed fields under `[tool.agent_maintainer]`:

```toml
runtime_events_enabled = false
runtime_events_dir = ".verify-logs/events"
runtime_event_history_limit = 14
runtime_event_level = "info"
runtime_events_include_debug = false
```

Downstream default should be disabled or very conservative during beta. This
repository should dogfood runtime events once implemented.

## Event Categories

Initial event coverage should focus on lifecycle and dogfood quality:

- `command.started`, `command.finished`, `command.failed`
- `profile.started`, `profile.finished`
- `check.selected`, `check.skipped`, `check.started`, `check.finished`,
  `check.failed`
- `hook.invoked`, `hook.noop`, `hook.failed`
- `dogfood.source_checkout_detected`, `dogfood.stale_install_warning`
- `artifact.written`, `artifact.retention_pruned`
- `provider.enabled`, `provider.skipped`
- `runtime.lock_wait`, `runtime.result_reused`, `runtime.run_fresh`
- `assessment.started`, `assessment.finished`

These events are not a replacement for `.verify-logs/runs/<run-id>/` artifacts.
They are a compact index of what happened and where to inspect details.

## Error Handling And Exceptions

Failure-path telemetry should be deliberate, compact, and safe:

- Expected check failures should emit `check.failed` with check name, profile,
  run id, exit code, duration, failure category, and the run-scoped artifact path.
- Unexpected exceptions should emit `command.exception`, `hook.exception`, or
  `check.exception` with exception type, sanitized message, run id or hook id,
  and artifact path for the full traceback when one exists.
- Runtime event records should not inline full tracebacks by default. Tracebacks
  belong in run-scoped logs or explicit debug artifacts, then events point to
  those files.
- Event flushing should be best-effort and crash-safe. A failure to write runtime
  events must not hide the original verifier/check failure.
- The runtime event writer should degrade to no-op with a warning if the event
  directory cannot be created or written.
- Redaction should run before writing exception messages. Avoid recording
  environment dumps, command output with possible secrets, bearer tokens, API
  keys, private file contents, or full user prompts.
- Failure events should include the same "likely next action" or artifact
  pointer philosophy as repair capsules: one useful next step, not a transcript.

Tests should cover exception paths explicitly:

- CLI command raises before run id creation.
- Check command exits non-zero.
- Check execution raises unexpectedly.
- Hook receives malformed stdin.
- Event directory is unwritable.
- Redaction removes obvious secret-like values from exception messages.
- Event writing failure does not change the primary command exit code.

## Logging Sufficiency

There is no widely accepted "logging coverage" metric equivalent to line or
branch test coverage. Counting log statements is usually the wrong target.
It rewards noise instead of useful observability.

Agent Maintainer should enforce event-contract coverage instead:

- Define required lifecycle events for each important runtime boundary:
  CLI command, verifier profile, check executor, hook adapter, artifact writer,
  retention pruning, source-checkout dogfood detection.
- Add tests with an in-memory event sink that assert each boundary emits
  required start, finish, failure, and skip events.
- Validate emitted JSONL events against a small schema.
- Assert events include correlation fields when a run id, profile, command,
  check, or hook id exists.
- Assert events do not include raw stdout/stderr, file contents, secrets, or
  obvious credential-like values.
- Add a dogfood report that summarizes recent event completeness, slow checks,
  reused runs, stale-install warnings, hook no-ops, and artifact pruning.

This is solvable. It becomes difficult only if the project tries to solve
distributed tracing, remote collection, arbitrary exporter configuration, and
semantic conventions for every provider at the same time. The first version
should stay local, bounded, schema-tested, and artifact-backed.

## Implementation Sequence

1. Add this roadmap and phase entry.
2. Add internal runtime event model, event names, severity enum, and in-memory
   test sink. Do not write files yet.
3. Add local JSONL writer and deterministic retention under
   `.verify-logs/events/`.
4. Instrument command, verifier, check executor, hook, artifact, retention, and
   dogfood-drift boundaries.
5. Add `assess dogfood` or `report runtime` output that summarizes recent event
   quality without printing raw logs.
6. Add event-contract tests and event schema tests.
7. Dogfood this repository with runtime events enabled.
8. Decide whether to add an optional `structlog` integration or OpenTelemetry
   export support after local events prove useful.

## Acceptance Criteria

- Normal agent-facing verification output remains summary-first.
- Runtime events are local, structured JSONL, and bounded by retention.
- Event records include stable event names, timestamps, severity, correlation
  ids, status, duration where relevant, and artifact pointers.
- Runtime logs never duplicate raw check transcripts already stored in
  run-scoped artifacts.
- Error and exception events are redacted, artifact-backed, and do not swallow
  or mask the original failure.
- Tests prove required lifecycle event contracts for CLI, verifier, executor,
  hooks, artifacts, retention, and dogfood-drift checks.
- This repository dogfoods runtime event emission before any downstream default
  becomes blocking.
- OpenTelemetry and `structlog` remain optional future choices unless evidence
  shows the internal writer is becoming a poor substitute.

## Non-goals

- No remote log shipping by default.
- No OpenTelemetry exporter in the first implementation phase.
- No dependency on `structlog` in the first implementation phase.
- No raw stdout/stderr duplication in event logs.
- No private file contents, secrets, environment dumps, or user data in events.
- No log-count coverage metric.
- No blocking downstream gate until dogfood evidence proves the event contract
  is stable and low-noise.
