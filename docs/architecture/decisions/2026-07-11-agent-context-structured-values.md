# 2026-07-11: Agent Context Structured Values

## Status

Accepted.

## Context

The reusable `agent_context` package consumes verifier manifests, attention
ledgers, repair facts, log metadata, and optional Headroom results. It already
validated decoded objects and arrays inside `failures`, but those helpers were
private to that module. Five other consumers repeated weaker runtime checks,
leaving every remaining production strict-Pyright diagnostic in the package
at structured-data boundaries.

The package must remain independent of `agent_maintainer`, so the
application-level structured-value helper is not an acceptable dependency.

## Decision

`agent_context.structured_values` owns the package-local JSON object and array
normalizers. The private helpers previously in `agent_context.failures` move
there unchanged. Attention rendering, Headroom compression, failure loading,
next-action ranking, and log selection may depend on the new leaf module.
Those dependency edges are recorded in `src/agent_context/tach.domain.toml`.

Compression request metadata uses an explicitly parameterized dictionary
factory. The Headroom callable and result contracts use `object` rather than
explicit `Any`, with normalization before dictionary traversal.

## Consequences

Decoded context data crosses one visible, runtime-validated boundary before
it is rendered or turned into commands. Pyright, IDEs, and future agents can
follow string-keyed objects and explicit array elements without reconstructing
implicit shapes across modules. Malformed neighboring entries are skipped,
while valid attention, log, and compression data remains available.

The new module is a dependency-free leaf, and `agent_context` remains reusable
without importing the main application package.

## Alternatives Considered

- Import `agent_maintainer.core.structured_values`. Rejected because it would
  reverse the package-independence boundary.
- Keep or duplicate private helpers in each consumer. Rejected because it
  fragments one provider-neutral contract and encourages behavior drift.
- Use unchecked casts, explicit `Any`, or suppressions. Rejected because those
  approaches hide malformed external shapes instead of validating them.

## Verification

Mapped tests cover mixed valid and malformed attention entries, Headroom
messages, and manifest checks. Existing failure, next-action, compression,
model, and log suites cover compatibility. Tach, Ruff, wemake, strict Pyright,
manual verification, and the CI-equivalent profile enforce the boundary.
