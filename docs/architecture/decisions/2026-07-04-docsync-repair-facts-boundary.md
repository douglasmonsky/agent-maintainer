# DocSync Repair Facts Boundary

## Status

Accepted.

## Context

DocSync verifier failures should surface exact repair facts in Agent Maintainer
repair capsules and context packs. `src/docsync/` is an extractable sibling
package and must not import `agent_maintainer` or `agent_repair_facts`.

## Decision

Add a DocSync JSON report parser under `agent_repair_facts.parsers.docsync`.
The parser reads DocSync's public JSON report shape and does not import the
`docsync` package. Agent Maintainer can register that parser for the `docsync`
check artifact while DocSync remains independent.

## Consequences

- DocSync failures can produce file and line repair facts.
- The DocSync package boundary remains clean.
- Repair-fact parsing owns verifier-facing normalization, not DocSync runtime.

## Alternatives Considered

- Import DocSync models directly in `agent_repair_facts`. Rejected because it
  would couple a reusable parser package to the extractable DocSync package.
- Parse only human log output. Rejected because JSON reports are structured and
  less brittle.
