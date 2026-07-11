# 2026-07-11: Attention Structured Signal Boundary

## Status

Accepted.

## Context

Attention scoring renders ledger payloads and recursively searches runtime-event
objects for known repository paths. Ledger payloads used a permissive `Any`
return type, and recursive mapping/list checks left nested keys and elements
unknown to strict Pyright. The signal context also used an untyped list factory.

The attention package is application code and may depend inward on the existing
dependency-free `agent_maintainer.core.structured_values` boundary.

## Decision

Ledger models expose `dict[str, object]`, rendering validates the files array,
and recursive signal walking normalizes JSON objects and arrays before traversal.
Objects with non-string keys and malformed neighboring values are ignored. The
signal context uses a typed performance-note factory.

The corresponding dependency edges are recorded in
`src/agent_maintainer/attention/tach.domain.toml`.

## Consequences

Attention inputs and outputs now have explicit structured boundaries. Pyright,
IDEs, and future agents can trace ledger files and nested runtime-event values
without permissive payload types. Valid known paths remain discoverable when
adjacent nested values are malformed.

No external dependency, suppression, cast, or permissive `Any` annotation is
introduced. Existing tuple traversal is intentionally dropped because the
boundary is JSON data, whose arrays decode as lists.

## Alternatives Considered

- Keep `Any` on ledger and event mappings. Rejected because it obscures the
  boundary for all consumers.
- Add local casts or strict suppressions. Rejected because they would conceal
  malformed external data.
- Introduce attention-specific structured helpers. Rejected because the core
  provider-neutral normalizers already express the required contract.

## Verification

A red-green regression case places a non-string-keyed object beside valid nested
paths. The attention suite covers ledger rendering, runtime-event extraction,
bounded artifacts, and signal context behavior. Tach, Ruff, strict Pyright, the
broad local verifier, and hosted CI enforce the boundary.
