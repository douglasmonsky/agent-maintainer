# Wait Sweeper Boundary

## Status

Accepted.

## Context

Durable wait records need a polling owner that can run outside the foreground
agent turn. The wait package already owns external wait adapters and compact
final wait result rendering.

## Decision

Add `agent_maintainer.wait.sweeper` inside the wait package. It owns one-shot
registry sweeps, watching a single wait until terminal state, and launching a
detached local watcher process.

## Boundary

The sweeper may depend on GitHub PR wait querying, wait registry records, and
wait output models. It must not import hooks, verifier internals, task broker
code, or Codex SDK runtime code.

## Alternatives Considered

- Put background polling in hooks. Rejected because hooks should remain
  lifecycle adapters and must not own long-running polling behavior.
- Put sweep behavior in the registry. Rejected because persistence and polling
  are separate responsibilities.

## Consequences

Hooks and future rewake backends can start or invoke the sweeper without
duplicating polling logic or foreground chatter.
