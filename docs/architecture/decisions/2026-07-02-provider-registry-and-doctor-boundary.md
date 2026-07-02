# Provider Registry And Doctor Boundary

## Status

Accepted.

## Context

Agent Maintainer now has a Python core provider plus experimental
TypeScript/JavaScript and Go providers. The catalog still preserves central
ordering so Python check behavior remains stable, but direct provider imports
in catalog construction make the next provider harder to add consistently.

Doctor output also needs provider-owned setup health. Generic executable checks
are useful, but they do not explain enabled providers with no configured
commands, and unknown non-Python tools previously fell back to Python-package
installation hints.

## Decision

Add a private built-in provider registry under `agent_maintainer.ecosystems`.
The registry owns metadata for built-in providers: name, display name, maturity,
docs path, capabilities, enabled config field, and configured command fields.

Catalog construction uses the registry for provider instances while keeping the
central check order intact. Doctor support uses provider metadata for compact
status rows and configured-command setup checks.

This is not an external plugin API. Provider loading remains built-in and
internal during beta.

## Consequences

- Python remains the core/reference provider and keeps its stable catalog order.
- Experimental providers gain explicit maturity and command ownership metadata.
- Doctor can report enabled providers with missing command configuration.
- Missing Node and Go tools can receive ecosystem-appropriate install hints.
- The next provider can follow the built-in registry pattern without direct
  catalog imports.

## Alternatives Considered

- Keep direct imports in the catalog. Rejected because the next provider would
  repeat catalog wiring and doctor metadata drift.
- Publish plugin entry points now. Rejected by the provider API stability ADR;
  the provider seam is still beta-internal.
- Move provider orchestration fully out of the catalog. Rejected because central
  ordering remains the safest way to protect Python behavior.
