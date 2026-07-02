# Neutral Git Change Reader

## Status

Accepted.

## Context

`assess reviewability` is advisory provider-aware reporting. It needs to see
changed files across enabled ecosystems before any Python-specific reviewability
policy is applied.

The existing `agent_maintainer.checks.change_budget` git numstat helper is
intentionally Python policy code. It excludes lockfiles, generated-like files,
and binary-heavy artifacts so the blocking Python `change-budget` gate remains
low-noise.

Reusing that helper for advisory TypeScript/JavaScript and Go reviewability
created hidden coupling: non-Python dependency files such as
`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, and `go.sum` could be
filtered before provider classification saw them.

## Decision

Add `agent_maintainer.ecosystems.git_changes` as a neutral git numstat reader
for provider-aware advisory reporting. It returns raw changed-path line counts
without Python path exclusions.

`assess.reviewability` now depends on this neutral reader instead of
`checks.change_budget`. The blocking Python `change-budget` gate keeps its
existing helper, exclusions, wording, and behavior.

## Consequences

- TypeScript/JavaScript lockfiles and Go dependency files stay visible in
  `assess reviewability`.
- Advisory reviewability can collect evidence without widening blocking gates.
- The provider layer owns neutral changed-path observation, while Python
  change-budget remains a Python policy implementation.
- Future provider-aware policy adapters can build on neutral observations
  without depending on Python filtering.

## Alternatives Considered

- Broaden `change_budget.run_git_numstat` to include non-Python files. Rejected
  because it risks changing the low-noise blocking Python gate.
- Keep advisory reviewability on the Python helper. Rejected because it hides
  non-Python dependency changes before provider classification.
- Add TypeScript/Go-specific git readers. Rejected because the git observation
  step is ecosystem-neutral; providers should classify paths after collection.
