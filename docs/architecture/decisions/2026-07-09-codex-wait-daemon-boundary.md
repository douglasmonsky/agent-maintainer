# Codex Wait Daemon Boundary

## Status

Accepted.

## Context

Codex background waits already write durable wait records and can attempt
automatic continuation through the Codex app-server rewake backend. The weak
link was watcher lifetime: a detached child process started from a tool turn can
be lost or outlive the useful Codex thread metadata. Heartbeat fallback works,
but it still wakes a model on every interval while the wait is pending.

## Decision

Add `agent_maintainer.wait.daemon` as the repo-scoped terminal wait owner for
macOS Codex rewake setups. When `AGENT_MAINTAINER_CODEX_REWAKE=1`, Codex thread
metadata is present, and a usable Codex CLI exists, background wait registration
ensures a user LaunchAgent named
`com.agent-maintainer.wait.<stable-root-hash>`. The LaunchAgent runs
`python -m agent_maintainer wait daemon run --root <repo>` and logs to
`.verify-logs/watchers/daemon.log`.

The daemon sweeps pending wait records quietly, consumes a short-lived rewake
envelope for ready records, attempts one Codex continuation through the existing
rewake backend, and leaves manual resume state intact when continuation fails.
Other platforms, disabled rewake, missing Codex metadata, or launchd failure use
the existing detached watcher and heartbeat fallback.

## Boundary

`daemon` may depend on `codex_rewake`, `registry`, and `sweeper`. It owns
launchd plist generation, bootstrap/status/uninstall commands, daemon heartbeat
metadata, and transient rewake envelopes.

The plist must not contain Codex thread ids, prompts, hook stdin, API keys, or
private payloads. Durable wait records must not contain those values either. The
only permitted thread handoff is `.verify-logs/watchers/<wait-id>/rewake-env.json`
with mode `0600`; the daemon deletes it after read and ignores expired or invalid
envelopes.

`codex_rewake` remains responsible for Codex app-server/SDK mechanics, feature
flag enforcement, continuation prompts, and marking records `resumed`.
`agent_waits` remains generic and does not learn launchd, GitHub, verifier, or
Codex app-server details.

## Alternatives Considered

- Keep detached `Popen(start_new_session=True)` watcher as the primary path.
  Rejected because its lifetime is best effort and it cannot reliably carry
  thread metadata after the initiating turn ends.
- Use a cheap model heartbeat as the primary watcher. Rejected because it still
  spends tokens every interval while pending.
- Persist Codex thread ids in wait records or plist environment. Rejected because
  durable repo state must remain free of client-session metadata and private
  payloads.

## Consequences

macOS Codex rewake can avoid model wakeups while waits remain pending. The
fallback behavior stays recoverable: users can run `wait resume <id>` or rely on
heartbeat prompts if launchd or rewake is unavailable. The wait domain now has an
explicit daemon module whose dependencies are declared in Tach.
