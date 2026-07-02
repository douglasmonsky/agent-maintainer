# ADR: Provider-Aware File Change Classification

## Status

Accepted.

## Context

Phase 94 documented that Agent Maintainer's reviewability checks are currently
globally scheduled but Python-backed. Future cross-ecosystem reviewability needs
provider-supplied changed-file facts before any TypeScript/JavaScript or Go
policy gate can be considered.

## Decision

Add `agent_maintainer.ecosystems.file_changes` as the internal seam that combines
existing provider file classifiers with an observed change kind. The module is
data-only: it does not run policy, change budgets, suppression budgets, file
length checks, structure checks, or test relevance checks.

Python remains always available because it is the core/reference provider.
Experimental TypeScript/JavaScript and Go classification is used only when the
corresponding provider is enabled.

## Consequences

- Future advisory policy work can consume explicit ecosystem, role, generated,
  ignored, and change-kind facts.
- Current blocking Python reviewability behavior remains unchanged.
- Tach now treats `ecosystems.file_changes` as an explicit module depending on
  provider classifiers and ecosystem models.
