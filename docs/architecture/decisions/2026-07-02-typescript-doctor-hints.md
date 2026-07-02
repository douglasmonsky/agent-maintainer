# TypeScript Provider Doctor Hints

## Status

Accepted.

## Context

Phase 83 added an experimental TypeScript/JavaScript provider that is disabled
by default and runs only explicit configured commands. That provider needs setup
health feedback when a repository opts in, but disabled providers should not add
doctor output noise.

## Decision

Add `agent_maintainer.doctor.support.typescript` as the owner of
TypeScript-provider setup rows. The full doctor command splats these rows into
the result list, so `enable_typescript = false` returns no row. When enabled,
the module reports missing command configuration, missing command executables,
or active configured TypeScript command checks.

## Rationale

This gives early TypeScript adopters concrete setup feedback without moving
provider-specific setup knowledge into generic optional-gate prose. It also
preserves the quiet-control-plane principle by keeping disabled experimental
support invisible.

## Alternatives

- Fold TypeScript messages into `check_optional_gates`. Rejected because that
  would make disabled experimental support noisier and less actionable.
- Add package-manager detection in doctor. Rejected because Phase 84 still avoids
  npm, pnpm, yarn, and bun assumptions.

## Boundary Rules

- TypeScript doctor support may inspect TypeScript provider config fields.
- It may check configured command executables using PATH plus repo-local
  `node_modules/.bin`, `.venv/bin`, and `venv/bin`.
- It must not infer commands, mutate config, or generate starter files.
- Core doctor output remains responsible for formatting and strict-mode exit
  behavior.
