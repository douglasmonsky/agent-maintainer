# Multi-Ecosystem Reviewability Policy

## Status

Accepted.

## Context

Agent Maintainer is now a Python-core provider with an experimental
TypeScript/JavaScript configured-command provider. The provider seam is real,
but deep reviewability policies are still Python-backed: change-budget,
suppression-budget, file-length, structure-cohesion, and source/test relevance.

Calling those policies fully language-neutral would overstate the current beta
state and could make future agents accidentally widen blocking behavior before
fixtures prove signal quality.

## Decision

Keep blocking reviewability policy Python-backed in the current beta.
TypeScript/JavaScript providers may provide classification, configured commands,
doctor rows, and structured repair facts, but classifications must not
automatically widen blocking Python reviewability checks.

Before any cross-ecosystem reviewability gate becomes blocking, add
provider-aware file-change classification and advisory output first. Blocking
cross-ecosystem policy requires explicit tests and configuration.

## Consequences

- Python behavior remains stable and protected.
- Public docs say Agent Maintainer is Python-core with experimental
  TypeScript/JavaScript support, without claiming reviewability parity.
- The next implementation phases have a clear target: introduce generic
  file-change classification behind tests.
- Experimental provider classifications remain preparatory until policy
  adapters mature.

## Alternatives Considered

- Aggregate TypeScript/JavaScript into `change-budget` immediately. Rejected
  because package layouts, generated files, and source/test conventions have not
  been proven across fixtures.
- Apply file-length and structure-cohesion to all provider source files now.
  Rejected because thresholds calibrated for Python may create noisy guidance in
  component-heavy TypeScript projects.
- Rename current checks to `python-*`. Rejected because check names are part of
  the current compatibility contract.
