# 2026-07-11: Configuration Structured Value Boundaries

## Status

Accepted.

## Context

Configuration loading and source validation consume user-authored TOML, while
reference generation and resolved validation traverse internally constructed
tuples. Plain dictionary and tuple checks left keys and elements unknown to
strict Pyright even though the runtime code already intended to reject malformed
tables and validate tuple contents.

These are different trust boundaries: TOML mappings require runtime string-key
validation, while internal tuples require only checked type narrowing.

## Decision

`config.loader`, `config.source_validation`, and the nested-table portion of
`config.reference` use the existing dependency-free
`agent_maintainer.core.structured_values` boundary. Their new dependency edges
are recorded in `src/agent_maintainer/config/tach.domain.toml`.

Configuration documents now expose `dict[str, object]` at their public loading
boundary. Shape errors retain their source-aware messages. Resolved path,
profile, reference, and tuple-value checks use narrow casts only after a runtime
`isinstance(value, tuple)` guard.

## Consequences

TOML tables have explicit string-keyed shapes before unknown-key discovery or
coercion. Malformed neighboring workspace and file-baseline entries remain
isolated and cannot hide valid configuration errors. Internal tuples retain
their existing behavior without being routed through a JSON abstraction.

Pyright, IDEs, and future agents can distinguish external configuration data
from resolved internal values. No dependency, suppression, or permissive type
was added.

## Alternatives Considered

- Cast TOML dictionaries directly. Rejected because user-authored table shapes
  require runtime validation, not an assertion.
- Route every tuple through structured-value helpers. Rejected because resolved
  tuples are trusted internal values and already have local runtime guards.
- Duplicate mapping validators inside the config package. Rejected because the
  application core already owns a stable provider-neutral boundary.
- Keep `dict[str, Any]` at public loader boundaries. Rejected because it hides
  the distinction between decoded data and validated configuration.

## Verification

Mapped tests cover malformed table roots, malformed neighboring dynamic tables,
source-aware errors, generated reference stability, path/profile constraints,
and tuple value checks. The full configuration suite, Tach, Ruff, strict
Pyright, file and change budgets, the broad verifier, and hosted CI enforce the
boundary.
