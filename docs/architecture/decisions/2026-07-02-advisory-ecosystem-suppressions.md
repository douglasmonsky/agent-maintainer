# ADR: Advisory Ecosystem Suppression Classification

## Status

Accepted.

## Context

The blocking `suppression-budget` gate is Python-backed.
TypeScript/JavaScript providers can classify changed files, but previously could
not expose ecosystem-specific suppression markers in advisory reviewability
output.

## Decision

Add provider-owned suppression classifiers for TypeScript/JavaScript. `assess
reviewability` may consume those classifiers after existing git diff helpers
report advisory suppression findings.

## Consequences

- TypeScript/JavaScript suppression markers become visible without changing
  blocking verifier behavior.
- Existing Python `suppression-budget` behavior stays unchanged.
- Assessment code has an explicit Tach dependency on provider suppression
  classifiers through the provider registry.
