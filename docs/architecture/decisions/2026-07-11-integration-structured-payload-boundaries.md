# 2026-07-11: Integration Structured Payload Boundaries

## Status

Accepted.

## Context

The standalone client-hook and run-artifact packages consume JSON settings and
verification artifacts. Runtime container checks left nested keys and elements
unknown to Pyright, while importing the main application's structured-value
helpers would reverse both packages' independence boundaries. The wait-registry
package had the same issue when decoding durable records, but already owned a
mapping normalizer suitable for that boundary.

## Decision

`agent_client_hooks.structured_values` owns dependency-free normalizers for
decoded string-keyed objects and arrays. Claude settings merge and removal may
depend on that leaf module.

`agent_run_artifacts.structured_values` separately owns dependency-free
normalizers for decoded objects, arrays, and arrays of objects. PR-summary
rendering may depend on that leaf module. These edges are recorded in each
package's `tach.domain.toml`.

The wait registry validates decoded records through its existing local mapping
normalizer. Direct reads reject non-object records with `WaitRegistryError`,
while enumeration retains its defensive behavior of skipping malformed files.

## Consequences

External JSON now crosses an explicit runtime-validated boundary before hook
mutation, debt-category ranking, or wait-record construction. Pyright, IDEs,
and future agents can follow string-keyed mappings and explicit element types
without reconstructing implicit shapes. Malformed neighboring entries cannot
hide otherwise valid hooks, debt drivers, or wait records.

The helpers remain package-local dependency-free leaves, so the standalone
packages gain no coupling to `agent_maintainer` or to each other.

## Alternatives Considered

- Import `agent_maintainer.core.structured_values`. Rejected because these
  integration packages must remain independently reusable.
- Share one new helper package. Rejected because coupling three small packages
  for primitive validation would add more architecture than it removes.
- Add casts, explicit `Any`, or suppressions. Rejected because those approaches
  hide malformed external shapes instead of validating them.
- Make malformed wait files abort enumeration. Rejected because it would break
  the registry's established fault-isolation behavior.

## Verification

Mapped tests cover valid hooks beside malformed entries, mixed debt-category
arrays, and direct versus enumerated malformed wait records. Tach, Ruff,
wemake, strict Pyright, the broad local verifier, and hosted CI enforce the
boundaries.
