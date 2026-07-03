<!-- docsync:evidence.start evidence.case_studies.cohesive_change_plan_fixture -->
# Cohesive Change Plan Example

This example shows how to make an intentionally larger change reviewable with a
checked change plan instead of bypassing the change budget casually.

## Run

From this directory, with Agent Maintainer installed:

```bash
git init
git add .
git commit -m "example baseline"
agent-maintainer change-plan check
agent-maintainer verify --profile precommit --base-ref HEAD
```

## Intentional Failure

The plan allows changes under `src/catalog/**` and `tests/**` only. A repair
agent should keep the migration inside that scope, explain why it should not be
split further, and run the verification plan from the change plan.

See [expected-output.md](expected-output.md) and [repair-path.md](repair-path.md).
<!-- docsync:evidence.end evidence.case_studies.cohesive_change_plan_fixture -->
