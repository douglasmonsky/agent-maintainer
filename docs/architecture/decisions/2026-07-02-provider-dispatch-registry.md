# Provider Dispatch Registry

## Status

Accepted.

## Context

The provider refactor introduced internal metadata for built-in providers, but
some reviewability helpers still imported provider-specific classification and
suppression modules directly. That was acceptable while TypeScript was the only
active experimental provider, but it would make the next provider spread
dispatch logic across assessment code.

## Decision

Provider-specific file classification and advisory suppression dispatch should
flow through `agent_maintainer.ecosystems.registry`. The registry remains
private/internal and owns only built-in provider wiring. `file_changes.py` and
`assess/reviewability.py` should call registry helpers instead of importing
concrete TypeScript or Python helper modules directly.

## Consequences

- Provider dispatch has one internal owner.
- Python and TypeScript behavior remains unchanged.
- The registry takes explicit dependencies on built-in provider classifiers and
  advisory suppression classifiers.
- This does not create an external plugin API or add another provider.

## Alternatives Considered

- Leave direct imports in assessment helpers: rejected because each future
  provider would add more branches outside the provider seam.
- Publish a public plugin API now: rejected because beta provider interfaces are
  still intentionally internal.
