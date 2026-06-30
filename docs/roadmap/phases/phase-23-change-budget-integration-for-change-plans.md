# Phase 23: Change-Budget Integration for Change Plans

## PR Title

```text
feat: allow planned large changes through scoped plans
```

## Files

Update:

```text
src/agent_maintainer/checks/change_budget.py
src/agent_maintainer/change_plan/*
```

## Behavior

A valid active plan can bend:

```text
change_warn_lines
change_block_lines
change_warn_files
change_block_files
source-without-test-change heuristic when allowed by plan
```

A plan cannot bend:

```text
tests
coverage
Pyright
Ruff
architecture checks
suppression budget
security checks
unsafe config checks
doctor freshness
generated guidance freshness
```

## Messages

Without plan:

```text
FAIL: Change budget exceeded

This change exceeds normal size limits.
If this is a cohesive migration, create a change plan:

  python -m agent_maintainer change-plan new <slug>

Do not raise change-budget thresholds directly.
```

With valid plan:

```text
CHANGE PLAN ACTIVE: package-migration-2026-06

Changed files: 84 / allowed 120
Changed lines: 8,900 / allowed 12,000
Out-of-plan paths: 0
Expired: no
Required sections: present

Normal change budget bent because this is an approved cohesive migration.
All other checks still apply.
```

## Acceptance Criteria

- Change budget bends only under valid plan.
- Out-of-plan changes fail.
- Other checks still run.
- Tests cover all plan states.
- Precommit passes.

---
