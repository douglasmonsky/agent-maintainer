# Mutmut Runner Lock Boundary

## Context

Agent Maintainer runs Mutmut from the manual profile and from focused runner
tests. Mutmut writes to a shared `mutants/` directory. A release-polish
baseline run exposed that overlapping Mutmut activity can make cleanup fail
or make one run read another run's generated artifacts.

## Decision

Add `agent_maintainer.runners.mutmut_lock` as a small runner-domain helper.
`agent_maintainer.runners.mutmut` now depends on that helper and keeps the
Mutmut command, result-ratchet export, and generated-artifact cleanup under
one cross-process lock.

The lock stays inside the `runners` domain because it protects a tool runner's
local generated artifacts. It does not belong in verifier locking, which
serializes whole verification runs based on repository state.

## Consequences

Concurrent direct Mutmut runner calls and manual verification now serialize
instead of racing over `mutants/`. The existing cleanup policy remains:
successful runs remove generated mutation artifacts unless
`AGENT_MAINTAINER_KEEP_MUTANTS=true` is set.

The Tach domain contract explicitly assigns the new helper module so future
runner support code remains visible rather than hidden under a broad module.
