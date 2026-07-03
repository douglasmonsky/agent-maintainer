# Architecture Decision: Runtime Events Foundation

Status: accepted

## What Changed?

The verifier may depend on the new `agent_maintainer.runtime_events` package to
emit compact local runtime lifecycle events. The config package also keeps
field-type coercion inventories in `agent_maintainer.config.schema_fields` so
`schema.py` stays under file-length limits while continuing to re-export the
same field constants to existing callers.

## Why Necessary?

Agent Maintainer needs dogfood-quality observability without expanding normal
agent-facing output. The verifier is the first high-value boundary because it
already owns profile execution, run ids, and diagnostic artifact locations.

## Why This Is Not Architecture Drift

Runtime events are an infrastructure support package with no dependency back
into the verifier. The verifier depends on the event model and sink, while the
event package stays small, local, dependency-free, and unaware of check
execution details.

## Alternatives Considered

1. Put event writing directly in `verify.quiet`. Rejected because logging
   policy, redaction, retention, and sink tests would be scattered.
2. Add OpenTelemetry immediately. Rejected because the current product need is
   local dogfood evidence, not remote observability infrastructure.
3. Defer all implementation. Rejected because local event contracts can now be
   tested cheaply without changing verifier output.

## Boundary Impact

`agent_maintainer.runtime_events` owns event serialization, redaction, sinks,
and retention. `agent_maintainer.verify.runtime_eventing` adapts verifier
profile lifecycle events to the runtime event sink so `verify.quiet` does not
own event storage policy. `agent_maintainer.config.schema` may depend on
`schema_fields`; `schema_fields` must remain dependency-free.

## What Remains Forbidden?

Do not make runtime events print raw check transcripts, prompts, environment
dumps, file contents, secrets, or tracebacks. Do not add remote log shipping,
OpenTelemetry exporters, or a logging dependency without a separate decision.

## Review Or Expiration Condition

Revisit when check-level, hook-level, or artifact-retention instrumentation is
added, or before introducing an optional OpenTelemetry exporter.
