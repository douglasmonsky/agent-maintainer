---
status: accepted
date: 2026-06-30
---

# Mutmut Result Ratchet Boundaries

## Context

Mutation result ratchets need to parse Mutmut's exported CI/CD stats in two
places:

- the Mutmut runner, which enforces configured budgets after `mutmut run`;
- the test-intelligence CLI, which gives humans and agents a compact summary of
  the same stats.

## Decision

Keep Mutmut stats parsing in `agent_maintainer.runners.mutmut_stats`, next to
the runner that produces and consumes those artifacts. Add a small
`agent_maintainer.test_intel.mutation_results` adapter for user-facing
rendering, and allow the test-intelligence CLI to depend on that adapter.

## Consequences

The runner remains responsible for execution and blocking ratchets. The
test-intelligence package remains responsible for advisory reporting. The
architecture contract explicitly names both modules so future changes cannot
hide broader runner/test-intelligence coupling.

## Alternatives Considered

Putting the parser directly in `test_intel.cli` was rejected because the CLI is
already near strict import and return-count limits. Putting result parsing under
`core` was rejected because Mutmut JSON is tool-specific, not a shared domain
model.
