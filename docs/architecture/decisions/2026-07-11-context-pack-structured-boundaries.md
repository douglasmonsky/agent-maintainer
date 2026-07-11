# 2026-07-11: Context Pack Structured Boundaries

## Status

Accepted.

## Context

Context-pack construction consumes optional attention entries, expansion
commands, omitted counts, and ratchet targets from nested payloads. Runtime
container checks left their keys and elements unknown to strict Pyright. Exact
fact budgets also used an untyped set factory, and attention helpers retained
permissive `Any` annotations.

The context-pack package is application code and may depend inward on the
existing dependency-free `agent_maintainer.core.structured_values` boundary.

## Decision

Attention entries, expansion-command arrays, omitted-count objects, and ratchet
target arrays normalize through `agent_maintainer.core.structured_values` before
use. The import-constrained builder delegates its generic payload accessors to
the existing supporting-context utility boundary and keeps compatible aliases.
Objects with non-string keys and malformed neighboring entries are ignored.
Exact-fact budgets use a typed path-set factory, and attention payload helpers
expose concrete object and iterable types.

The corresponding dependency edges are recorded in
`src/agent_maintainer/context/tach.domain.toml`.

## Consequences

Optional context data crosses an explicit validated boundary before it changes
repair facts, expansion guidance, or ratchet commands. Pyright, IDEs, and future
agents can trace string-keyed mappings and object arrays without reconstructing
implicit shapes.

No external dependency, suppression, cast, or permissive `Any` annotation is
introduced. Malformed optional records fail closed without hiding valid
neighboring context.

## Alternatives Considered

- Keep local `isinstance` checks and permissive types. Rejected because they do
  not establish nested key and element visibility.
- Add casts or strict suppressions. Rejected because those approaches would
  conceal malformed persisted data.
- Introduce pack-specific normalization helpers. Rejected because the existing
  core provider-neutral boundary already expresses the required contracts.

## Verification

A red-green regression test covers an attention entry with a non-string key.
Mapped tests also cover malformed ratchet targets, expansion-command elements,
and omitted counts. Context-pack, exact-fact safety, Tach, Ruff, strict Pyright,
the broad local verifier, and hosted CI enforce the boundary.
