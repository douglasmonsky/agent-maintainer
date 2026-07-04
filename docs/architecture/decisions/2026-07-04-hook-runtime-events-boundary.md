# 2026-07-04: Hook Runtime Events Boundary

## Status

Accepted

## Context

Phase 145 expands runtime event dogfooding beyond verifier profile and check
events. Agent-client hooks are an important runtime boundary because they decide
whether a coding agent can continue after an edit or final verification step.
The hook runtime already owns hook payload handling, configured-repository
no-op behavior, verifier invocation, hook audit records, and hook-specific
block output.

Runtime events are stored by the `agent_maintainer.runtime_events` package and
configured through `agent_maintainer.config`. Writing hook events requires the
hook runtime to create a sink for the target repository, but hooks should not
take ownership of event serialization, retention, or redaction.

## Decision

Add `agent_maintainer.hooks.runtime_eventing` as a narrow adapter owned by the
hooks package. It may depend on:

- `agent_maintainer.config.loader`;
- `agent_maintainer.config.schema`;
- `agent_maintainer.runtime_events.models`;
- `agent_maintainer.runtime_events.sinks`.

`agent_maintainer.hooks.runtime` may depend on this adapter. The adapter emits
compact hook invocation, finish, and exception events only for repositories that
are already configured for Agent Maintainer hooks. Unconfigured repositories
remain no-op and do not receive event artifacts.

## Why This Is Not Architecture Drift

The dependency points from hook orchestration to a narrow infrastructure adapter
for local runtime observability. Hook runtime still does not own event storage
internals. Runtime event packages remain independent of hook behavior.

This preserves the existing configured-repository safety rule while making hook
behavior dogfood-observable for this repository.

## Alternatives Considered

- Emit hook events directly from `agent_maintainer.hooks.runtime`.
  Rejected because it would mix config loading, event sink creation, and hook
  control flow in one module.
- Move hook orchestration into the runtime event package.
  Rejected because runtime events should observe hooks, not own hook behavior.
- Avoid hook runtime events until OpenTelemetry is introduced.
  Rejected because Phase 145 deliberately favors local JSONL event contracts
  before any optional exporter.

## Still Forbidden

- Hook runtime must not write raw verifier output, prompts, environment dumps,
  or tracebacks into runtime event records.
- Hook runtime must not run Agent Maintainer checks outside repositories with
  `[tool.agent_maintainer]`.
- Runtime event packages must not import hook runtime modules.
