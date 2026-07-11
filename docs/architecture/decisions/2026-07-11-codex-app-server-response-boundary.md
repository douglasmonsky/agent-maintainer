# 2026-07-11: Codex App-Server Response Boundary

## Status

Accepted.

## Context

The Codex app-server continuation client consumes JSON-RPC responses containing
nested thread and turn objects. The protocol parser used unchecked casts, while
the client narrowed generic mappings and lists that left nested keys and values
unknown to strict Pyright.

Both modules are wait infrastructure and may depend inward on the existing
dependency-free `agent_maintainer.core.structured_values` boundary.

## Decision

The protocol parser normalizes JSON-RPC error and result objects before creating
typed responses. The client then normalizes direct turns, thread objects, and
turn arrays before selecting the active turn. Malformed neighboring entries and
objects with non-string keys are ignored.

The corresponding dependency edges are recorded in
`src/agent_maintainer/wait/tach.domain.toml`.

## Consequences

App-server data crosses an explicit validated boundary before continuation state
changes. The response contract is a concrete string-keyed dictionary, so
Pyright, IDEs, and future agents can trace nested turn state without reconstructing
generic mappings.

No external dependency, suppression, cast, or permissive `Any` annotation is
introduced. The existing unchecked casts are removed, and all new architecture
edges point inward to a core validation utility.

## Alternatives Considered

- Keep generic mappings and add local casts. Rejected because casts would hide
  malformed JSON-RPC shapes.
- Duplicate guards in the protocol and client. Rejected because the repository
  already owns tested structured-value normalizers.
- Reject an entire thread response for one malformed neighboring turn. Rejected
  because valid terminal state should remain observable.

## Verification

A red-green regression test covers a nested turn object with a non-string key.
The app-server suite covers invalid roots, malformed neighboring turns, terminal
states, and polling. Tach, Ruff, strict Pyright, the broad local verifier, and
hosted CI enforce the boundary.
