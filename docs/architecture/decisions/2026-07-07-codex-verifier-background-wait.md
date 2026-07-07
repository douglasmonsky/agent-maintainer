# Codex Verifier Background Wait Boundary

## Status

Accepted.

## Context

Codex `wait verifier` commands already convert to durable background waits, but
the common repo wrappers `just v` and `just vc` call `agent_maintainer verify`
directly. That left the most common long-running validation path as a foreground
tool call, causing repeated pending-status chat updates.

## Decision

When `agent_maintainer verify` runs inside Codex and foreground waits are not
explicitly allowed, start the existing async verifier child, register a generic
`agent_waits` verifier wait record, start a quiet watcher, and render the same
structured heartbeat handoff used by known wait commands.

## Boundary

`agent_maintainer.verify` may depend on standalone `agent_waits` primitives for
Codex environment policy, durable generic wait records, and handoff rendering.
It must not import `agent_maintainer.wait` adapters. The wait CLI remains the
owner of verifier polling and resume rendering; the verifier package only starts
the detached `agent_maintainer wait sweep --watch` process.

This is reflected in `src/agent_maintainer/verify/tach.domain.toml` by allowing
`quiet` and `background_wait` to depend on `agent_waits` primitives while keeping
`agent_maintainer.wait` out of the verifier package dependencies.

## Alternatives Considered

- Change only the `just` recipes to add `--async`. Rejected because direct
  verifier invocations would still foreground-block Codex.
- Let `verify` import `agent_maintainer.wait.broker`. Rejected because that
  creates a sideways package dependency from verifier orchestration into wait
  CLI adapters.
- Keep manual guidance only. Rejected because this problem is easy to regress
  and expensive in repeated chat turns.

## Consequences

Common Codex validation commands now use the background wait and heartbeat
contract by default. Local foreground validation remains available with
`AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1`.
