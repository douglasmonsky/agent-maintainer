# Architecture Decision: Add DocSync Sibling Package

Status: accepted

## What Changed?

Add a top-level `docsync` package under `src/` with its own CLI entrypoint,
repository configuration under `.docsync/`, and Tach boundary ownership.

## Why Necessary?

DocSync is planned as a documentation traceability and freshness layer. It needs
to evolve inside this repository first, but the package is intended to be
extractable and usable by other repositories later.

## Why Is This Not Just Architecture Drift?

The new boundary is explicit: DocSync may depend on the standard library and
generic third-party packages, but must not import `agent_maintainer` or
`archguard`. The Tach contract and extraction-boundary test enforce that.

## Alternatives Considered

1. Put DocSync under `agent_maintainer.docsync`.
2. Start a separate repository immediately.
3. Keep the implementation as scripts until the shape is clearer.

The sibling package keeps the work local while preserving a clean extraction
path and avoiding an accidental dependency on Agent Maintainer internals.

## Boundary Impact

`docsync` owns documentation traceability, freshness checks, review packets, and
attestations. Agent Maintainer may later call DocSync through its public API,
but DocSync must not call back into Agent Maintainer. The knowledge graph,
vector retrieval, GraphQL, and wiki prototype is preserved on
`experiment/docsync-knowledge-graph` and remains outside this accepted package
boundary until it earns a separate design decision.

## What Remains Forbidden?

DocSync must not import `agent_maintainer` or `archguard`, add broad Tach
ignores, or relax existing architecture checks to make package growth pass.

## Review Or Expiration Condition

Revisit this decision before extracting DocSync into a standalone distribution
or before allowing Agent Maintainer adapters to call DocSync in CI.
