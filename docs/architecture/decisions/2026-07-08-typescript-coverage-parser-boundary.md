# TypeScript Coverage Parser Boundary

## Status

Accepted.

## Context

Phase 167 added TypeScript/React repair facts for Vitest task JSON, Istanbul
`coverage-summary.json`, and LCOV artifacts. Keeping test-output diagnostics
and coverage artifact parsing in one module pushed
`agent_repair_facts.parsers.typescript_diagnostics` over the repository
source-line limit.

## Decision

Move TypeScript coverage artifact parsing into
`agent_repair_facts.parsers.typescript_coverage` and Vitest task-style parsing
into `agent_repair_facts.parsers.typescript_tests`. Keep
`typescript_diagnostics` focused on compiler, ESLint, and Jest diagnostics.
The Agent Maintainer compact-summary and ecosystem compatibility shims may
depend on these reusable parser modules explicitly.

## Why This Is Not Architecture Drift

The split narrows a growing parser module by responsibility. It does not add a
new product dependency, framework detector, package-manager inference, coverage
gate, or broad Tach ignore. Dependencies still point inward to reusable
`agent_repair_facts` parsers.

## Alternatives Considered

Leaving coverage parsing in `typescript_diagnostics` would require suppressing
or ignoring the file-length gate. Moving shared diagnostic models into another
module would be broader than needed for this repair.

## Consequences

Coverage artifact support remains reusable by context packs and compact
summaries, while diagnostic parsing stays below structural limits.
