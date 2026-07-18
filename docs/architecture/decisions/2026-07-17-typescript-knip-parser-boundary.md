# TypeScript Knip Parser Boundary

## Status

Accepted.

## Context

Phase 179 adds one explicit TypeScript Knip check whose JSON output serves two
consumers: compact verifier summaries in `agent_maintainer.core` and exact
repair facts in `agent_repair_facts`. Root and workspace checks also need one
narrow check-family normalizer. Parsing the same third-party JSON separately in
both consumers would allow supported categories, malformed-input behavior, and
bounds to drift.

## Decision

Keep Knip JSON validation, category normalization, repository-relative path
validation, deterministic sorting, and the 500-finding retention bound in
`agent_repair_facts.parsers.typescript_knip`. Keep the TypeScript check-name
normalizer in dependency-free `agent_repair_facts.parsers.typescript_checks`.

Allow `agent_repair_facts.registry` to depend on both modules for exact fact
dispatch. Allow `agent_maintainer.core.structured_typescript` to depend on both
reusable modules so compact summaries consume the same normalized findings and
workspace-name contract. Declare only those exact dependencies in the two Tach
domain files.

## Why This Is Not Architecture Drift

The change follows the existing TypeScript diagnostics, tests, and coverage
parser direction: product-facing reporting depends inward on reusable parsing.
It adds no Node dependency, package-manager inference, command mutation, broad
Tach ignore, or reverse dependency from repair facts into Agent Maintainer.

## Alternatives Considered

Duplicating a smaller Knip parser in `agent_maintainer.core` would remove one
declared dependency but create two schema and safety implementations. Moving
the parser into the ecosystem provider would couple reusable repair facts to
provider execution. Treating all Knip output as generic logs would discard the
approved exact-fact and compact-summary value.

## Consequences

Knip schema handling and safety fixes apply to both summaries and repair facts.
The core reporting domain gains two narrow, explicit parser dependencies, and
future Knip category expansion must update the shared parser and its synthetic
and public compatibility evidence.
