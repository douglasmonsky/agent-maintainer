# Context Compression Backend Boundary

## Status

Accepted.

## Context

Phase 25 adds deterministic context compression contracts and built-in backends
before any optional external compression dependency exists. The new modules must
remain explicit under Tach because this repository uses `root_module = "forbid"`.

## Decision

Assign `agent_maintainer.context.compression` to the models layer because it
contains immutable request/result contracts only.

Assign `agent_maintainer.context.compression_backends` to the runtime layer
because it performs deterministic backend selection, truncation, extraction, and
fallback validation.

## Consequences

Compression backends may depend on the compression contract, but the contract
must not depend on backend implementations or external services. Optional
provider integrations belong in future runtime modules and must not move the
contract out of the models layer.

## Alternatives Considered

Putting both modules in runtime was rejected because the request/result objects
are stable boundary contracts. Putting backend selection in orchestration was
rejected because the Phase 25 backends are deterministic library behavior, not a
CLI or workflow adapter.

## Still Forbidden

Deterministic compression backends must not import optional provider SDKs,
network clients, CLI modules, verifier orchestration, or hook runtime code.
