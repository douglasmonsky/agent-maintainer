# Experimental TypeScript Provider Boundary

## Status

Accepted.

## Context

Agent Maintainer now has a Python provider seam and file classification adapters
that preserve current Python behavior. Phase 83 adds the first non-Python
provider to validate that seam without adding package-manager autodetection,
starter-file generation, public plugin loading, or TypeScript-specific repair
facts.

## Decision

Add `agent_maintainer.ecosystems.typescript` as an internal experimental
provider. It owns TypeScript/JavaScript file classification and explicit
configured-command checks. The central catalog still owns ordering and verifier
composition. Core verifier code still owns execution, diagnostics, output,
reports, hooks, and repair-loop surfaces.

The provider is disabled by default. When enabled, it runs only commands from
`[tool.agent_maintainer]`:

- `typescript_lint_command`;
- `typescript_typecheck_command`;
- `typescript_test_command`.

## Rationale

This keeps the first non-Python provider honest and narrow. JavaScript
repositories vary across npm, pnpm, yarn, bun, ESLint, Biome, Jest, Vitest, and
framework-specific conventions. Guessing commands would create noisy setup
failures and weaken user trust. Explicit commands let early adopters opt in
without forcing a lowest-common-denominator provider model.

Python remains the reference provider. The TypeScript provider starts smaller
than Python on purpose and must not constrain future Python features.

## Alternatives

- Add package-manager autodetection now. Rejected because it expands scope before
  the provider seam has been proven by a non-Python provider.
- Add starter files and doctor rows in the same change. Rejected to keep Phase 83
  focused on provider wiring and behavior-preserving catalog integration.
- Put TypeScript checks directly in the central catalog. Rejected because that
  repeats the pre-provider architecture pressure the refactor is meant to solve.

## Boundary Rules

- TypeScript provider files may depend on shared ecosystem models and the shared
  `Check` model.
- The catalog may depend on the TypeScript provider to compose checks.
- The TypeScript provider must not own run-scoped diagnostics, summaries,
  reports, hooks, or repair plans.
- Do not add external plugin loading until multiple built-in non-Python
  providers have validated the internal seam.
- If a future abstraction makes Python-specific behavior harder to express,
  redesign the abstraction instead of weakening Python behavior.
