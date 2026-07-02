# ADR: Advisory Reviewability Assessment

## Status

Accepted.

## Context

Phase 95 introduced provider-aware file-change classifications, but no
user-facing command consumed them. Provider stabilization feedback called for
low-noise advisory visibility before any cross-ecosystem policy gate becomes
blocking.

## Decision

Add `assess reviewability` as an advisory assessment command. The command may
depend on the existing git numstat parser and provider classification models,
but it must not call or alter blocking verifier checks.

## Consequences

- Users can inspect changed files by ecosystem and role before policy adapters
  mature.
- TypeScript/JavaScript findings remain advisory.
- The `assess.reviewability` Tach module explicitly depends on provider
  classification models and the existing change-budget diff parser.
