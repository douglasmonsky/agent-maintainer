# Codex App-Server Rewake Boundary

## Status

Accepted.

## Context

Codex terminal rewake needs a local JSON-RPC client for
`codex app-server --listen stdio://`. The client owns process startup, JSON-RPC
line parsing, turn completion detection, and quiet `thread/read` fallback
polling. Keeping that protocol code inside `agent_maintainer.wait.codex_rewake`
pushed the rewake backend over the repository file-size ratchet.

## Decision

Add `agent_maintainer.wait.codex_app_server` as a wait-layer leaf module. The
module owns Codex app-server protocol mechanics and exposes only the
continuation-client protocol plus `CodexAppServerClient`. The rewake backend may
depend on this helper while remaining responsible for feature flags, wait-record
state transitions, SDK fallback, and privacy-preserving manual fallback.

## Boundary

`codex_app_server` must stay a leaf infrastructure helper. It may use standard
library process, thread, queue, and JSON primitives. It must not import wait
handlers, wait registry, runtime events, GitHub/verifier polling, CLI modules, or
durable wait records. It must not persist Codex thread ids, prompts, hook stdin,
API keys, environment dumps, or app-server payloads.

`codex_rewake` may import `codex_app_server`, `handlers`, `registry`, and
`agent_waits.models`. This is not architecture drift because the new dependency
extracts an existing implementation detail from the same adapter boundary and
does not add a new outward dependency.

`handlers` consumes verifier wait results through `verifier` rather than
`verifier_manifest` so cached verifier jobs and manifest parsing share one
terminal-result boundary.

## Alternatives Considered

- Keep app-server code inside `codex_rewake`. Rejected because it violates the
  file-size ratchet and mixes protocol mechanics with wait-record orchestration.
- Move app-server code into `agent_waits`. Rejected because Codex app-server is
  maintainer/Codex-specific infrastructure, not reusable wait-domain state.
- Relax the file-size or Tach checks. Rejected because the split provides a
  clearer ownership boundary without weakening guardrails.

## Consequences

Codex rewake remains optional and feature-flagged, while app-server protocol
behavior has focused tests and a smaller module boundary. Future terminal
rewake hardening should keep app-server mechanics in `codex_app_server` and keep
wait lifecycle decisions in `codex_rewake`.
