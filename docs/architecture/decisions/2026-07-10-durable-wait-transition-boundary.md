# Durable Wait Transition Boundary

## Status

Accepted.

## Context

Terminal wait completion, Codex notification, detached watchers, and the
repo-scoped daemon can all observe the same wait record from different
processes. Plain atomic file replacement protects JSON integrity, but it does
not make a read-modify-write transition exclusive. A stale pending writer could
therefore overwrite a terminal state, and two notification or repair workers
could both act on the same record.

The wait lifecycle also needs recoverable watcher metadata without persisting
Codex thread ids, prompts, commands, environment values, or backend diagnostics.

## Decision

Keep cross-process transition primitives in the generic `agent_waits` domain:

- `record_lock` owns short-lived, per-wait filesystem locks;
- `notifications` owns the fail-closed
  `ready_for_manual_resume -> notifying -> resumed | notify_failed` state
  machine; and
- `watcher_state` owns bounded watcher lifecycle metadata and atomic repair
  claims.

Registry read-modify-write operations re-read the current record while holding
the same per-wait lock. Notification is claimed before any external Codex call.
An abandoned, failed, or visibly unconfirmed attempt becomes manual-only and is
not retried automatically. Watcher repair checks current liveness while holding
the lock before it starts a replacement.

The `agent_maintainer.wait` adapter may depend on these generic primitives to
integrate launchd, detached processes, the Codex app-server, and the CLI.
`agent_waits` must not depend on those platform-specific adapters.

Keep platform-specific adapters narrow: app-server protocol helpers own JSON-RPC
messages and parsing, launchd helpers own detached process launch, and rendering
modules own text/JSON output. Coordination modules may re-export stable entry
points, but those responsibilities must not collapse back into one CLI or
sweeper module.

Wait adapters may emit lifecycle events only after the corresponding durable
claim or state transition. `wait.ready` uses a separate once-only observation
claim; registration, successful watcher start, and rendered fallback also use
per-wait observation claims so idempotent registration cannot duplicate them.
Notification attempts occur only after the notification claim, and a resume
event requires persisted `resumed` state. Fallback handoffs expose a
deterministic exponential backoff contract instead of implying fixed short
cadence.

## Boundary

Durable watcher metadata is limited to strategy, positive process id when one
exists, start time, last poll time, repair-claim time, and fixed failure codes.
The transition modules must never persist commands, environment variables,
thread ids, prompts, credentials, terminal payloads beyond the existing wait
record contract, or raw exception text.

Lifecycle event attributes are similarly allowlisted to stable wait identity,
terminal status, safe strategy, numeric cadence facts, and fixed failure codes.
They exclude process ids, commands, labels, log paths, Codex context, and raw
backend diagnostics.

Locks protect only brief local state transitions. External processes and Codex
calls run outside the lock after a durable claim has been written. Stale
notification claims fail closed; watcher repair is explicit and never calls
Codex.

## Alternatives Considered

- Rely only on atomic JSON replacement. Rejected because it prevents partial
  files but not lost updates or duplicate external work.
- Put locking and repair policy in the Codex adapter. Rejected because verifier,
  GitHub, and future wait kinds share the same durable registry races.
- Persist complete watcher commands or Codex context for automatic recovery.
  Rejected because recovery metadata must remain privacy-safe and portable.
- Retry notification after a timeout. Rejected because a process can fail after
  Codex accepted the request, making a retry capable of spending another model
  turn or duplicating continuation.

## Consequences

Wait transitions are serialized per record without a repository-wide lock.
Notification favors at-most-once external work and manual recovery over
automatic retry. Watcher repair can restore dead polling while preserving a
small, non-sensitive durable footprint. The Tach domain manifests now declare
these dependencies explicitly.
