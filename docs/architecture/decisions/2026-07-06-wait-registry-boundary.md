# Wait Registry Boundary

## Status

Accepted.

## Context

Background PR waits need durable state so an agent can stop foreground polling
and later resume from a compact result. The existing wait adapters already own
polling external work and rendering compact final wait results.

## Decision

Add `agent_maintainer.wait.registry` inside the wait package. It owns
file-backed wait records under `.verify-logs/waits/`, registration output, and
manual resume rendering for wait commands.

## Boundary

The registry remains an adapter-level wait concern. It may depend on existing
wait result models and GitHub PR wait renderers. It must not import hook,
verification, repair, CLI orchestration, or Codex SDK runtime code.

## Alternatives Considered

- Put wait records in hook code. Rejected because hooks should only detect and
  hand off lifecycle events.
- Store records in the verifier run log model. Rejected because PR waits are
  external waits and should not pretend to be verifier runs.

## Consequences

Future background sweepers and optional rewake backends can consume the same
registry without changing the existing foreground waiter output contract.
