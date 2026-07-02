# Python Provider Boundary

## Status

Accepted.

## Context

The ecosystem-provider roadmap requires Python to become the first internal
provider before Agent Maintainer adds any non-Python ecosystem support. Phase 77
added characterization tests for current Python catalog behavior. Phase 78 moves
Python check construction behind a private provider seam while keeping
`catalog.make_checks()` responsible for final ordering.

## Decision

`agent_maintainer.catalogs.catalog` may depend on the private
`agent_maintainer.ecosystems.python.provider` module to retrieve Python-owned
checks. The catalog remains the verifier integration point and still composes
global checks, architecture checks, security checks, docs/config checks, and
ecosystem checks in the existing order.

The new `agent_maintainer.ecosystems` package is internal. It is not a public
plugin API, does not load external packages, and does not add language support.
The Python provider is allowed to keep Python-specific capabilities such as
Pyright, pytest coverage, Mutmut, Bandit, pip-audit, Deptry, Vulture, wemake,
Interrogate, and diff-cover.

The ecosystem package has its own Tach domain file so every provider module is
explicitly assigned. `agent_maintainer.catalogs.catalog` may depend on the
provider package, but provider modules should not depend on verifier execution,
hook adapters, reports, or doctor orchestration.

## Alternatives Considered

- Keep Python construction directly in the catalog. This would preserve current
  behavior but would leave no seam for later provider work.
- Move ordering into the provider. This would overfit Phase 2 and make global
  check ordering harder to reason about.
- Introduce external plugin discovery now. This is premature because the
  provider interface has not survived multiple built-in ecosystems.

## Consequences

Python behavior remains protected by characterization tests while the catalog
now has an explicit dependency on the internal provider package. Future phases
can separate global and ecosystem-owned checks more cleanly without changing the
verifier execution engine or public CLI behavior.
