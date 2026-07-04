# Quiet Wait Boundary

## Status

Accepted.

## Context

The priority-one cadence waste roadmap needs commands that own waiting for
long-running work instead of making agents poll GitHub Actions, verifier jobs,
or hook-launched checks from chat. The first implementation is a quiet GitHub
Actions run waiter.

## Decision

Add `agent_maintainer.wait` as a small package for wait adapters and shared
compact repair-capsule rendering. The package currently owns the GitHub Actions
adapter and a shared wait output model. Top-level CLI routing may lazy-load the
wait CLI, but polling behavior and wait result formatting stay inside the wait
package.

## Alternatives Considered

- Put the GitHub polling wrapper directly in the root CLI. Rejected because the
  local verifier waiter and hook-visible readiness work would duplicate result
  formatting and polling conventions.
- Build a scheduler framework immediately. Rejected because the current need is
  a thin waitable-work contract, not a second job orchestration system.

## Boundary Guardrails

- `agent_maintainer.wait` owns polling adapters and compact final status
  rendering for waitable work.
- Wait adapters should emit summary-first repair capsules and keep raw logs in
  the backing system or run artifacts.
- The wait package must not own verifier execution, hook installation, or GitHub
  workflow configuration.
- Future adapters should share run id, state, timeout, stale-state, final result,
  and exact next-command semantics before adding client-specific behavior.
