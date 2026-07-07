# Known Wait Handler Registry

## Status

Accepted.

## Context

Background PR waits proved durable wait registry Codex handoff pattern, but
sweeper still hardcoded GitHub PR polling. GitHub run waits and local verifier
waits need the same quiet background behavior without moving
maintainer-specific polling into the reusable `agent_waits` package.

## Decision

Add a handler registry under `agent_maintainer.wait`. Handlers own
maintainer-specific registration, one-shot polling, terminal result mapping,
and continuation prompts for `github-pr`, `github-run`, and `verifier` waits.
`agent_waits` remains generic and only owns durable records, compact capsules,
foreground-wait policy, and structured heartbeat request rendering.

Codex hook runtime may depend on the wait broker to convert same-state pending
verifier readiness into a background wait handoff.

This updates architecture policy in:

- `src/agent_maintainer/hooks/tach.domain.toml`
- `src/agent_maintainer/wait/tach.domain.toml`

## Why This Is Not Drift

The hooks dependency on the wait broker is limited to a Codex pending verifier
handoff; polling remains in the wait layer. The handler registry keeps GitHub
and verifier adapters in `agent_maintainer.wait` instead of leaking them into
the reusable `agent_waits` package.

## Alternatives Considered

1. Keep the PR-only sweeper and add separate foreground commands for GitHub run
   and verifier waits. Rejected because Codex would still foreground-poll known
   waits.
2. Move all polling into `agent_waits`. Rejected because that package is the
   generic durable-record and rendering layer, not the maintainer-specific
   GitHub/verifier adapter layer.

## What Remains Forbidden

Do not put arbitrary tool interception in this slice. Do not persist Codex
thread ids, hook stdin, API keys, prompts from user context, or private payloads
in wait records.

## Consequences

Known wait kinds share one sweep/watch path, Codex foreground wait enforcement
applies consistently without broad arbitrary tool interception. Future wait
kinds add handlers instead of branching the sweeper.
