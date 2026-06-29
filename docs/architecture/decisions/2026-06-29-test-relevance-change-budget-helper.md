# Architecture Decision: Test Relevance Change-Budget Helper

Status: accepted

## Context

Phase 8 makes change-budget warnings more actionable by using test intelligence
to identify likely relevant tests. Adding that logic directly to
`change_budget.py` pushed the module over the configured member limit, which is
treated as a refactor signal in this repository.

## Decision

Extract the new source/test relevance guidance into
`agent_maintainer.checks.test_relevance` and keep `change_budget.py` focused on
diff parsing, budget calculations, and command orchestration.

The new module is assigned to the runtime layer with the other check helpers.
It may depend on test-intelligence mapping and config models, but it must not
decide verifier pass/fail behavior beyond returning warning text.

## Alternatives Considered

Suppressing the module-member finding was rejected because the warning pointed
to a real responsibility split.

Putting the helper under `test_intel` was rejected because the warning policy is
specific to the change-budget check.

## Still Forbidden

Test relevance guidance remains advisory. It must not make source-without-test
warnings more punitive unless a later policy phase explicitly changes that.
