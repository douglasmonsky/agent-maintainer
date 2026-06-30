# Phase 24: Integration Branch Series

## PR Title

```text
feat: support integration branch change plans
```

## Plan Fields

Add:

```toml
kind = "integration-branch-series"
integration_branch = "ratchet/package-migration"
target_branch = "main"
merge_strategy = "squash-after-series"
expected_units = [
  "move config modules",
  "move check modules",
  "update tests",
  "update docs and generated guidance",
]
```

## Behavior

Final PRs from integration branches receive planned-large-change semantics only when the plan is valid.

## Acceptance Criteria

- Branch fields validated.
- Invalid branch state fails plan check.
- Out-of-plan paths still fail.
- Tests fixture git branch state.
- Precommit passes.

---
