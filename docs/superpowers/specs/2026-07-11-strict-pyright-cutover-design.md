# Strict Pyright Dogfood Cutover Design

## Context

Agent Maintainer introduced a disabled-by-default strict-Pyright ratchet so
existing repositories could improve incrementally without making strict mode an
immediate zero-error gate. The Agent Maintainer repository used that migration
path while its reviewed baseline fell from 1,298 diagnostics to zero. The
migration is now complete: strict Pyright analyzes 740 files with no errors.

## Decision

Promote the Agent Maintainer repository's ordinary Pyright configuration from
`standard` to `strict`. Disable its migration-only strict ratchet, remove the
repository's zero-error baseline artifact, and remove the explicit baseline and
max-error dogfood settings from `pyproject.toml`.

Keep the reusable strict-ratchet runner, configuration fields, generated
configuration reference, and consumer documentation intact. Other repositories
may still need a reviewed per-file/per-rule baseline while migrating.

## Alternatives Considered

1. Keep the zero baseline. This remains correct but leaves duplicate strict
   checks and a migration artifact with no remaining debt to represent.
2. Teach the ratchet runner to operate without a baseline at zero. This adds a
   second permanent zero-error enforcement path when ordinary strict Pyright
   already provides the required behavior.
3. Promote normal Pyright to strict and retire only this repository's baseline.
   This is the selected approach because it is simpler, exercises the product's
   standard verifier path, and preserves consumer migration support.

## Configuration and Verification Flow

The repository's full and hosted verification profiles already execute ordinary
Pyright. After the cutover, that existing check generates a strict configuration
and fails on any new diagnostic. The manual-profile ratchet is disabled for this
repository, so it no longer requires or generates comparison evidence during
normal dogfood verification.

Verification must prove:

- ordinary Pyright runs in strict mode and reports zero diagnostics;
- the strict-ratchet check is absent or skipped for this repository;
- configuration loading and generated references remain current;
- the deleted baseline has no remaining repository-specific reference;
- the complete local and hosted verifier matrices pass.

## Documentation and Roadmap Evidence

Add a completion note to the strict-typing roadmap phase recording that the
dogfood repository reached zero and promoted its ordinary Pyright gate to
strict. Preserve historical stabilization evidence that describes the ratchet
when it was necessary.

## Rollback

Revert the cutover commit to restore `standard` ordinary checking, re-enable the
ratchet, and restore the reviewed zero baseline. No production API or persisted
consumer data changes are involved.
