# Architecture Decision: Change-Plan Authority Over Legacy Overrides

Status: accepted

## Context

Active change plans can fail because the plan is invalid, expired, or outside
the allowed scope. Those failures describe authority problems with the current
change, not ordinary size-budget failures.

The older cohesive-change override is intentionally narrower: it can accept a
large but coherent diff when the repository has opted into that exception. It
must not clear active change-plan validation failures.

Adding that distinction directly to `change_budget.py` pushed the module over
the configured member limit.

## Decision

Move legacy override application into
`agent_maintainer.checks.change_budget_overrides`.

`change_budget.py` remains responsible for parsing the diff and orchestrating
the check. `change_budget_overrides` decides whether a legacy cohesive-change
override may clear current failures. It treats failures starting with
`Change plan invalid:` as authoritative and leaves them blocking even when a
cohesive-change override is otherwise eligible.

`cohesive_override` now exposes a minimal changed-file protocol instead of
depending on the concrete `FileChange` class from `change_budget.py`.

## Alternatives Considered

Keeping the helper in `change_budget.py` was rejected because the module-member
finding points to a real responsibility split.

Letting cohesive-change override clear all failures was rejected because it
would allow a legacy escape hatch to bypass the stricter change-plan contract.

## Still Forbidden

Cohesive-change override remains a narrow exception for size-budget failures.
It must not clear invalid, expired, or out-of-scope active change plans.
