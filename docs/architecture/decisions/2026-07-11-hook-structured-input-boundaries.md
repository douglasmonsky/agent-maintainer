# 2026-07-11: Hook Structured Input Boundaries

## Status

Accepted.

## Context

Hook runtimes consume JSON from stdin, verifier readiness files, and nested tool
responses. Runtime container checks left decoded keys and elements unknown to
strict Pyright. Recursive PR-response extraction also needed to ignore malformed
fields without hiding valid neighboring text.

Hook application code may depend inward on the existing dependency-free
`agent_maintainer.core.structured_values` boundary.

## Decision

Root hook, readiness, and runtime payloads normalize through strict JSON-object
validation. Recursive PR-response extraction uses a new core object-item helper
that filters non-string fields while preserving valid neighbors. Arrays use the
existing explicit element boundary.

The corresponding dependency edges are recorded in
`src/agent_maintainer/hooks/tach.domain.toml`.

## Consequences

Hook inputs cross an explicit runtime boundary before they trigger PR waits,
readiness decisions, or stop-hook behavior. Pyright, IDEs, and future agents can
trace string-keyed data without reconstructing implicit JSON shapes. A malformed
nested field no longer contributes text and does not obscure valid siblings.

No external dependency, suppression, cast, or permissive `Any` annotation is
introduced in the changed hook boundaries. Existing hook ownership and outward
side-effect constraints remain unchanged. Independent mutation-state typing is
deferred to the next bounded batch.

## Alternatives Considered

- Reject an entire nested object for one malformed field. Rejected because valid
  response text should remain available for PR handoff detection.
- Add hook-local casts or suppressions. Rejected because those approaches would
  conceal malformed external data.
- Duplicate object-item normalization in the hook. Rejected because the behavior
  is provider-neutral and reusable at other structured boundaries.

## Verification

A red-green regression test covers a malformed PR-response field beside valid
nested text. Core helper coverage fixes the filtering contract. The full hook
suite, Tach, Ruff, Flake8, strict Pyright, the broad local verifier, and hosted
CI enforce the boundary.
