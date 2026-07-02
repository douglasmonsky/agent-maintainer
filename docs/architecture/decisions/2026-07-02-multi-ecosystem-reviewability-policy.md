# Multi-Ecosystem Reviewability Policy

## Status

Accepted.

## Context

Agent Maintainer now has a Python core provider plus experimental
TypeScript/JavaScript and Go configured-command providers. The provider seam is
real, but the deep reviewability policies are still Python-backed:
change-budget, suppression-budget, file-length, structure-cohesion, and
source/test relevance.

Calling those policies fully language-neutral would overstate the current beta
state and could make future agents accidentally widen blocking behavior before
fixtures prove the signal quality.

## Decision

Keep blocking reviewability policy Python-backed for the current beta.

TypeScript/JavaScript and Go providers may continue to provide classification,
configured commands, doctor rows, and structured repair facts, but their
classifications must not automatically widen blocking Python reviewability
checks.

Before any cross-ecosystem reviewability gate becomes blocking, add
provider-aware file-change classification and advisory output first. Blocking
cross-ecosystem policy requires explicit tests and configuration.

## Consequences

- Python behavior remains stable and protected.
- Public docs can say Agent Maintainer is Python-core with experimental
  TypeScript/JavaScript and Go providers without claiming reviewability parity.
- The next implementation phase has a clear target: introduce generic
  file-change classification behind tests.
- Experimental provider classifications remain preparatory until policy
  adapters mature.

## Alternatives Considered

- Aggregate TypeScript/JavaScript and Go into `change-budget` immediately.
  Rejected because package layouts, generated files, and source/test
  conventions have not been proven across fixtures.
- Apply file-length and structure-cohesion to all provider source files now.
  Rejected because the thresholds are calibrated for Python and may create
  noisy guidance for component-heavy TypeScript projects or Go package layouts.
- Rename current checks to `python-*`. Rejected for now because check names are
  part of the current compatibility contract.
