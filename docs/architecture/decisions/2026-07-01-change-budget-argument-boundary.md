# Change Budget Argument Boundary

## Status

Accepted.

## Context

`agent_maintainer.checks.change_budget` was near the file-length warning zone and mixed
diff-budget domain behavior with command-line parsing and config override wiring. The
module is a blocking reviewability gate, so keeping the behavior compact and easy to
audit matters.

## Decision

Move CLI parsing and root-override normalization into
`agent_maintainer.checks.change_budget_args`. Keep tiny compatibility wrappers in
`change_budget.py` so existing tests and internal callers that import
`change_budget.parse_args`, `change_budget.parse_csv_like`, or
`change_budget.apply_cli_overrides` continue to work.

Update the local Tach domain contract so `change_budget` may depend on
`change_budget_args`, and `change_budget_args` may depend only on core config types.

## Alternatives Considered

- Split Git diff collection first. That is also a reasonable future boundary, but the
  parser/config override cluster was smaller and lower risk.
- Move all public helpers and update every caller. That would create avoidable churn
  without improving the architecture.

## Consequences

`change_budget.py` is smaller and more focused on budget behavior. The argument module
has no dependency on diff execution, change-plan evaluation, or test relevance logic.
