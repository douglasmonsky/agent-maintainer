# Policy Checks Use Python Classifier Adapters

## Status

Accepted.

## Context

Phase 80 introduced an internal Python file classifier, but existing policy
checks still owned direct `.py`, generated-file, ignored-path, source-root, and
test-root decisions. Phase 81 starts moving those Python-specific decisions
behind the provider boundary while preserving current check behavior.

## Decision

Allow policy checks and test-intelligence mapping to depend on
`agent_maintainer.ecosystems.python.classification` for Python path predicates.
The checks remain responsible for their policy decisions and output contracts;
the Python provider owns Python path roles.

## Rationale

This keeps the core policy checks from scattering Python path rules while still
avoiding a premature generic provider API. The dependency points are narrow:
source path, test path, Python file, generated Python file, and ignored Python
path predicates.

## Alternatives

- Keep `.py` and root checks inside each policy module. Rejected because it
  duplicates Python assumptions and makes future provider extraction noisier.
- Create a generic language-neutral policy adapter now. Rejected because only
  Python is implemented and the abstraction would be speculative.

## Boundary Rules

- Policy checks may ask the Python classifier about path roles.
- The Python classifier must not import policy checks.
- Providers do not own verifier orchestration, diagnostics, reports, or hook
  behavior.
- If classifier predicates make Python policy behavior harder to express, stop
  and redesign the adapter rather than weakening Python behavior.
