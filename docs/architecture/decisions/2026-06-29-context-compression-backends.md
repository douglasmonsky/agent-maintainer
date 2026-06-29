# Context Compression Backend Boundary

## Status

Accepted.

## Context

Phase 25 adds deterministic context compression contracts and built-in
backends before any optional external compression dependency exists. New
modules must remain explicit under Tach because this repository uses
`root_module = "forbid"`.

## Decision

Assign `agent_maintainer.context.compression` to the models layer because it
contains immutable request/result contracts only.

Assign `agent_maintainer.context.compression_backends`,
`agent_maintainer.context.headroom_backend`, and
`agent_maintainer.context.pack_compression` to the runtime layer because they
perform backend selection, optional provider adaptation, truncation,
extraction, and fallback validation for sanitized supporting context.

## Consequences

Compression backends may depend on the compression contract, but the contract
must not depend on backend implementations or external services. Optional
provider integrations belong in runtime modules and must not move the contract
out of the models layer.

## Alternatives Considered

Putting both modules in runtime was rejected because request/result objects are
stable boundary contracts.

Putting backend selection in orchestration was rejected because Phase 25
backends are deterministic library behavior, not a CLI or workflow adapter.

## Still Forbidden

Compression code must not send exact repair facts, structured manifests,
ratchet fingerprints, change-plan scopes, or raw unredacted logs to optional
providers. Provider adapters must receive only sanitized supporting context.
