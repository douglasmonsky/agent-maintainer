# Quiet Wait Boundary

## Status

Accepted.

## Context

The priority-one cadence waste roadmap needs commands to own waiting for
long-running work instead of making agents poll GitHub Actions, verifier jobs,
or hook-launched checks from chat. The first implementation added a quiet
GitHub Actions run waiter, followed by a local verifier manifest waiter.

## Decision

Add the small `agent_maintainer.wait` package for wait adapters, verifier
manifest reading, and shared compact repair-capsule rendering. The package
currently owns GitHub Actions run and PR-check adapters, local verifier
artifact waiter, and shared wait output model. Top-level CLI routing may lazy-load wait CLI, but
polling behavior and wait result formatting stay inside the wait package.

Async verifier launch state stays in `agent_maintainer.verify.async_jobs`
because it starts verifier execution and records verifier-specific process
metadata. The wait package consumes completed verifier manifest by run id; it
does not supervise verifier execution. Hook-visible readiness stays in
`agent_maintainer.hooks.readiness`: hooks may inspect same-state verifier locks
and completed-result records, then emit the same wait-oriented capsule without
starting another verifier process. Repository discovery for hooks stays in
`agent_maintainer.hooks.discovery` so runtime orchestration does not own Git
probing or executable lookup.

## Alternatives Considered

- Put GitHub polling wrapper directly in root CLI. Rejected because local
  verifier waiter and hook-visible readiness work would duplicate result
  formatting and polling conventions.
- Build scheduler framework immediately. Rejected because the current need is a
  thin waitable-work contract, not a second job orchestration system.

## Boundary Guardrails

- `agent_maintainer.wait` owns polling adapters and compact final status
  rendering for waitable work.
- `agent_maintainer.wait.verifier_manifest` owns the narrow manifest view used
  by local verifier wait output; it must not become a second artifact schema.
- `agent_maintainer.verify.async_jobs` may create background verifier jobs, but
  it must hand agents back the same wait repair-capsule contract used by wait
  adapters.
- `agent_maintainer.hooks.readiness` may read verifier lock/result metadata to
  avoid duplicate same-state hook work, but it must not execute verifier checks
  or own artifact schemas.
- `agent_maintainer.hooks.discovery` owns lightweight repo/executable
  discovery for hook entrypoints.
- Wait adapters should emit summary-first repair capsules and keep raw logs in
  the backing system or run artifacts.
- The wait package must not own verifier execution, hook installation, or
  GitHub workflow configuration.
- Future adapters should share run id, state, timeout, stale-state, final
  result, and exact next-command semantics before adding client-specific
  behavior.
