# 2026-07-10: Fail-Closed Configuration Boundary

## Status

Accepted.

## Context

Agent Maintainer configuration is accepted from `pyproject.toml`, neutral TOML
files, environment variables, verifier flags, named workspaces, and file
baseline groups. The former implementation described those surfaces in
separate field sets. Unknown nested keys could be dropped, Python booleans were
accepted as integers, and several sources did not enforce bounds or
cross-field policy before commands were constructed.

## Decision

`agent_maintainer.config.registry` is the authoritative field contract. Each
resolved field declares its canonical TOML path, compatibility aliases, value
kind, resolved default, constraints, environment capability, CLI capability,
documentation label, and stability. Nested-table keys are declared beside that
registry. The schema owns low-level named constants and dataclass construction;
the registry reads those defaults without creating a schema-to-registry cycle.

Raw source names are checked by `config.source_validation` before coercion.
Type-specific resolved checks live in `config.value_types`, source-aware issues
live in `config.issues`, and `config.validation` composes type, bound, path,
profile, nested-structure, and cross-field rules. The loader validates after
each file/environment merge, and verifier CLI overrides validate the complete
resolved policy before returning it.

Nested diagnostic and file-baseline TOML paths are canonical. Established
top-level spellings remain explicit compatibility aliases, but specifying an
alias and its canonical key together is an error rather than an
order-dependent override.

The config domain may depend on the shared profile model for profile-name
validation. The core argument domain may depend on config validation because
CLI overrides are the final verifier-specific merge boundary. These edges are
recorded explicitly in
`src/agent_maintainer/config/tach.domain.toml` and
`src/agent_maintainer/core/tach.domain.toml`. The root command edge is recorded
in `tach.toml`: `agent_maintainer.cli` may load configuration and handle its
typed validation error through `config.preflight` before routing behavior. CLI
and stability declarations live in `config.registry_capabilities` so the
authoritative registry remains inside the repository's file-length ratchet.

## Consequences

Adding a `MaintainerConfig` field without registering it fails drift tests.
Typos and invalid policy stop with the physical source and dotted public key.
All environment capabilities are derivable from the same data used for
coercion and reference generation. `config.reference` renders the public
Markdown inventory and versioned JSON capability payload, while a currentness
test prevents either artifact from drifting. Compatibility remains intentional
and testable instead of relying on permissive key discovery.

Repository-scoped input paths must remain relative and may not traverse above
the checkout. Diagnostic and runtime-event output directories retain absolute
path compatibility because callers use owned temporary destinations.

## Alternatives Considered

- Keep independent field sets in the loader, metadata, and schema. Rejected
  because drift is what allowed sources to enforce different policy.
- Warn for unknown keys. Rejected because a typo can silently weaken a
  guardrail while the command continues.
- Remove all legacy top-level spellings. Rejected because valid existing
  configuration can migrate without weakening fail-closed behavior.
- Validate only file and environment input. Rejected because mode and CLI
  overrides can create contradictions after those earlier checks.

## Verification

Registry drift and environment round-trip tests cover all resolved fields.
Table-driven tests cover typos at every nesting level, source-aware neutral
file errors, boolean/integer confusion, numeric bounds, cross-field ordering,
compression contradictions, repository-relative paths, profile names,
compatibility aliases, alias conflicts, and file/environment/CLI precedence.
