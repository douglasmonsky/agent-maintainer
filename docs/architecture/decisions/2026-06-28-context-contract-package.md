# Architecture Decision: Context Contract Package

Status: accepted

## Context

The context-safe legacy ratchet roadmap needs shared primitives for bounded
agent-facing output, exact repair facts, sanitized supporting context, and
untrusted excerpt labels. These contracts will be used later by verifier,
hook, reporting, and repair-plan code.

Because this repository uses Tach with `root_module = "forbid"`, the new
`agent_maintainer.context` package must have an explicit architecture layer.

## Decision

Add `agent_maintainer.context.models` to the `models` layer. Add
`agent_maintainer.context`, `agent_maintainer.context.budget`,
`agent_maintainer.context.formatting`, and `agent_maintainer.context.sanitize`
to the `shared` layer.

This keeps dataclasses dependency-light and allows runtime, orchestration, and
entrypoint code to depend inward on stable context contracts.

## Alternatives Considered

Keeping these primitives under `verify` was rejected because hooks, reports,
and future repair-plan commands will also need them.

Putting everything in `models` was rejected because budget, sanitization, and
formatting helpers are behavior around the models, not pure value objects.

## Still Forbidden

The context package must not import verifier execution, hook runtime,
subprocess orchestration, filesystem scanning, or tool-specific runners.
