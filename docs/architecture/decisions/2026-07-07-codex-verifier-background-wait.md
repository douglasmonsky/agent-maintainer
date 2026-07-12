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
explicitly allowed, start the existing async verifier child and register its
wait through the typed `agent_maintainer.wait.broker` service. The broker owns
the persisted record and watcher policy while verifier code renders the same
structured heartbeat handoff used by known wait commands.

The async launch is a durable lifecycle rather than a bare `Popen` call:

1. atomically persist `starting` state and stable stdout/stderr destinations;
2. spawn a new session with `stdin=DEVNULL`, owned log handles, and
   `close_fds=True`;
3. persist `running` only after capturing the child PID;
4. have the owned child entrypoint wait for that running record before invoking
   verifier behavior; and
5. atomically persist `passed`, `failed`, `error`, or `cancelled` with the real
   process exit code.

The detached wait watcher follows the same noninteractive stream and descriptor
contract. A spawn or child infrastructure failure is terminal `ERROR`, not a
quality-check `FAIL` and not a pending record that eventually masquerades as a
timeout.

## Boundary

`agent_maintainer.verify` may call the typed wait broker registration service
and depend on standalone `agent_waits` primitives for Codex environment policy,
durable generic wait records, and handoff rendering. Handlers, registry
internals, daemon, launchd, sweeper, polling, resume, and rewake remain
forbidden to verifier code.

The one-way polling dependency is explicit: `agent_maintainer.wait.verifier`
may read `agent_maintainer.verify.async_state` so it can convert child lifecycle
records into truthful terminal wait records. Async verifier code does not import
the wait adapters.

This is reflected in `src/agent_maintainer/verify/tach.domain.toml` by allowing
`background_wait` to depend on the typed wait broker and `agent_waits` broker.

## Alternatives Considered

- Change only the `just` recipes to add `--async`. Rejected because direct
  verifier invocations would still foreground-block Codex.
- Keep a second verifier-owned launcher. Rejected because it duplicates watcher
  policy and persisted lifecycle ownership.
- Move launchd into `agent_waits`. Rejected because platform daemon integration
  remains product-owned.
- Add an extra forwarding wrapper. Rejected because the typed broker is already
  the canonical registration boundary.
- Keep manual guidance only. Rejected because this problem is easy to regress
  and expensive in repeated chat turns.

## Consequences

Common Codex validation commands now use the background wait and heartbeat
contract by default. Local foreground validation remains available with
`AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1`.

A POSIX pseudo-terminal integration test closes the launcher's fd 0 before
spawn, exits the parent, closes the terminal, and requires the detached verifier
to produce its real manifest without a bad-file-descriptor failure.
