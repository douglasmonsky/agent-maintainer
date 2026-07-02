# ADR: Advisory Ecosystem Suppression Classification

## Status

Accepted.

## Context

The blocking `suppression-budget` gate is Python-backed. TypeScript/JavaScript
and Go providers can classify changed files, but previously could not expose
ecosystem-specific suppression markers in advisory reviewability output.

## Decision

Add provider-owned suppression classifiers for TypeScript/JavaScript and Go.
`assess reviewability` may consume these classifiers and existing git diff
helpers to report advisory suppression findings.

## Consequences

- TypeScript/JavaScript and Go suppression markers become visible without
  changing blocking verifier behavior.
- Existing Python `suppression-budget` behavior stays unchanged.
- Assessment code now has an explicit Tach dependency on provider suppression
  classifiers and the existing suppression diff helper.
