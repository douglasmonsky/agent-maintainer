# 2026-07-04: Command Runtime Events Boundary

## Status

Accepted

## Context

Phase 145 expands runtime events from verifier profile, check, and hook events
to the top-level Agent Maintainer command boundary. Command events are useful
for local dogfood analysis because they show which command surfaces agents use
and whether failures happen before a verifier run exists.

The CLI package should remain a thin router. Runtime event serialization,
redaction, retention, and best-effort writer behavior already belong to
`agent_maintainer.runtime_events`.

## Decision

Add `agent_maintainer.runtime_events.commands` as a narrow adapter for
top-level command lifecycle events. `agent_maintainer.cli` may depend on this
adapter. The adapter may depend on:

- `agent_maintainer.config.loader`;
- `agent_maintainer.runtime_events.models`;
- `agent_maintainer.runtime_events.sinks`.

The adapter emits `command.started`, `command.finished`, and
`command.exception` events when runtime events are enabled. It records compact
metadata such as command name, duration, exit code, status, and argument count.
It does not record raw argv values.

## Why This Is Not Architecture Drift

The dependency keeps command observability at the command boundary while
preserving the CLI's routing responsibility. Runtime events remain local,
best-effort, and independent of normal command output. Configuration load
failures in the event adapter degrade to no-op so event instrumentation does
not change command behavior.

## Alternatives Considered

- Emit command events inside every subcommand. Rejected because it would
  duplicate lifecycle logic and make event coverage inconsistent.
- Make the runtime event sink own CLI routing. Rejected because runtime events
  observe commands; they must not control routing.
- Record full argv for debugging. Rejected because command lines often contain
  paths, tokens, or prompts. The event contract favors safe correlation over
  raw transcripts.

## Still Forbidden

- Command events must not include raw argv, environment dumps, stdout/stderr,
  tracebacks, prompts, file contents, or secrets.
- Runtime event failures must not mask command exit codes or exceptions.
- Runtime event packages must not import command implementations.
