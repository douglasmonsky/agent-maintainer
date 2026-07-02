# Global Check Catalog Boundary

## Status

Accepted.

## Context

The ecosystem-provider roadmap separates core/global verifier responsibilities
from ecosystem-owned check generation. Phase 78 moved Python check construction
behind an internal Python provider, but the central catalog still contained
language-neutral reviewability, architecture, and workflow helper code.

## Decision

Move language-neutral check builders into
`agent_maintainer.catalogs.global_checks`. The central
`agent_maintainer.catalogs.catalog` module remains the final composition and
ordering point for verifier checks, but it no longer owns the implementation
details for file length, structure cohesion, change budget, suppression budget,
architecture checks, or workflow checks.

Python-specific tools stay behind `agent_maintainer.ecosystems.python.provider`.
Docs/config and generic security catalog helpers remain separate global catalog
modules.

## Alternatives Considered

- Keep all helper code in `catalog.py`. This preserved behavior but made
  global-vs-ecosystem ownership harder to see.
- Move ordering into providers. This would blur provider responsibility and
  make global check ordering less explicit.
- Generalize policy checks through file classifiers now. That belongs to a
  later phase after global and ecosystem ownership is visible.

## Consequences

The catalog Tach contract now depends on `global_checks` and the Python provider
explicitly. The verifier output and check order remain protected by
characterization tests while future phases can migrate policy checks toward
provider/classifier adapters more safely.
