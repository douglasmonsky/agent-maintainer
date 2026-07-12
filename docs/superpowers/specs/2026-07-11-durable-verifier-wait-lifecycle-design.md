# Durable Verifier Wait Lifecycle Design

**Date:** 2026-07-11

**Status:** Approved direction, written contract

## Problem

Direct Codex verifier runs register a generic `agent_waits` record and then
start their own detached `Popen` watcher in
`agent_maintainer.verify.background_wait`. Other wait entry points register
through `agent_maintainer.wait.broker`, which chooses launchd when required and
persists watcher strategy, PID, and failure state. The split produces different
truth for the same wait kind and was reproduced by `just vp` reporting
`watcher: started via popen` while the canonical wait command correctly
reported that launchd was required but unavailable.

## Goals

- Give every verifier wait one registration and watcher-start lifecycle.
- Persist the selected watcher strategy or stable failure code in the wait
  record before returning the registration capsule.
- Preserve the reusable `agent_waits` package as product-neutral state and
  notification infrastructure.
- Keep verifier code out of polling, resume, rewake, launchd, and process
  ownership.

## Non-goals

- Making launchd available on unsupported hosts.
- Falling back to detached `Popen` for strict Codex rewake when launchd is
  required.
- Moving platform-specific launchd code into `agent_waits`.
- Changing foreground verifier behavior or the verifier result protocol.

## Chosen architecture

`agent_maintainer.wait.broker` remains the canonical application-level
registration service. `agent_maintainer.verify.background_wait` will construct
one `BackgroundVerifierWait` and delegate to the existing
`register_background_verifier` specialization. Its local `start_wait_watcher`
function and `subprocess`/`sys` ownership will be removed.

This is an intentional narrow dependency from the verifier launch adapter to
the wait registration service. The verifier may request registration and render
the returned capsule; it must not import handlers, sweeper, daemon, launchd,
rewake, or registry internals. The Tach domain contract will name the broker
dependency explicitly, and the 2026-07-07 background-wait ADR will be amended
to distinguish **registration delegation** from forbidden **wait ownership**.

Adding another wrapper or protocol would only rename the same application
dependency. The broker's typed request and result objects are already the
narrow interface needed here.

## Data flow

1. The quiet verifier launches its asynchronous child and receives the run ID
   and log directory.
2. `verify.background_wait` requests a verifier registration from
   `wait.broker` with the current repository root, five-second interval, and
   one-hour timeout.
3. The broker's verifier handler creates or reuses the durable wait record.
4. `start_registered_watcher` tries the strongest supported watcher:
   launchd first; a strict Codex record fails closed when launchd is required;
   non-strict platforms may use detached `Popen`.
5. Watcher state is written through `agent_waits.watcher_state` before a
   `BackgroundWaitRegistration` is returned.
6. Verifier output renders that one durable result. Pending polling and
   terminal continuation remain owned by the wait subsystem.

## Error behavior

- Unsupported launchd for a strict Codex wait returns a successful wait
  registration with `watcher_started=false`, stable error code
  `launchd_required`, and the existing fallback-heartbeat capsule.
- A process-launch failure records `watcher_start_failed` and returns the
  bounded error text.
- Registration failures continue to fail at the existing registry/handler
  boundary; verifier code does not create a second record or watcher as a
  fallback.

## Alternatives considered

- **Keep both launchers and synchronize metadata.** Rejected because two
  lifecycle owners will drift again and still make policy selection ambiguous.
- **Move launchd selection into `agent_waits`.** Rejected because the extracted
  package is intentionally product- and platform-adapter-neutral.
- **Add a new forwarding service between verify and wait.** Rejected because
  the broker already exposes a typed registration boundary; another wrapper
  would hide rather than reduce coupling.

## Test strategy

- First add a failing verifier integration test showing that direct background
  registration delegates to the canonical broker request.
- Cover launchd success, strict-Codex unsupported launchd, and non-strict
  process fallback through existing broker seams.
- Assert persisted watcher strategy/PID or failure code by rereading the wait
  record, not merely by inspecting a mock call.
- Keep rendering tests for the fallback-heartbeat capsule.
- Run the verify and wait focused suites, the architecture tests, Tach exact
  checks, then the repository's broad profile.

## Acceptance criteria

- `verify.background_wait` contains no detached-process launcher.
- A direct Codex verifier wait and a CLI-registered verifier wait select the
  same watcher policy and persist the same state shape.
- Strict Codex never silently reports a `Popen` watcher when launchd is
  required.
- Tach and the amended ADR describe the narrow dependency and preserve all
  other forbidden wait ownership.
