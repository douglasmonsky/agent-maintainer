# Background PR Wait Hook Boundary

## Status

Accepted.

## Context

Codex PR wait hooks currently hand foreground agents a `wait github-pr` command.
Durable wait records and sweepers now provide a background wait path, but hooks
should remain lifecycle adapters rather than polling owners.

## Decision

Allow `agent_maintainer.hooks.pr_wait` to depend on the wait registry and
sweeper. The hook may register a wait record and launch the detached watcher
when explicitly enabled by `AGENT_MAINTAINER_BACKGROUND_PR_WAIT=1`.

## Boundary

The hook must not poll GitHub in the Codex background path. It may only detect
PR creation, register the wait, start the wait-package sweeper, and emit compact
continuation context. If watcher startup fails, it must fall back to the
existing foreground waiter handoff.

## Alternatives Considered

- Poll directly inside the hook. Rejected because hooks should not own
  long-running external wait loops.
- Enable background waits by default. Rejected until the feature has dogfood
  evidence across Codex sessions.

## Consequences

Codex can opt into less chatty PR waits without changing Claude async-rewake
behavior or the default Codex handoff path.
