# Phase 22: Cohesive Change Plans

## PR Title

```text
feat: add cohesive change plans
```

## Files

Create:

```text
src/agent_maintainer/change_plan/__init__.py
src/agent_maintainer/change_plan/cli.py
src/agent_maintainer/change_plan/models.py
src/agent_maintainer/change_plan/parser.py
src/agent_maintainer/change_plan/validation.py
src/agent_maintainer/change_plan/git_scope.py
src/agent_maintainer/change_plan/templates.py
```

## File Location

```text
.agent-maintainer/change-plans/<slug>.md
```

## Format

Use TOML front matter between `+++` delimiters.

Example:

```markdown
+++
id = "package-migration-2026-06"
kind = "mechanical-migration"
status = "active"
base_ref = "origin/main"
expires = "2026-07-15"
allowed_paths = ["src/agent_maintainer/**", "tests/**", "pyproject.toml", "tach.toml"]
forbidden_paths = ["config/prod/**"]
max_changed_files = 120
max_changed_lines = 12000
allow_source_without_test_change = true
requires_tests = true
requires_full_verify = true
ratchet_targets = ["src/legacy/big_service.py"]
+++

# Cohesive Change Plan: Package migration

## Why this change is intentionally large

...

## Why this should not be split smaller

...

## What is allowed to change

...

## What must not change

...

## Verification plan

...

## Rollback plan

...

## Follow-up ratchet work

...
```

## Commands

```bash
python -m agent_maintainer change-plan new package-migration
python -m agent_maintainer change-plan status
python -m agent_maintainer change-plan check
python -m agent_maintainer change-plan explain
```

## Required Sections

```text
Why this change is intentionally large
Why this should not be split smaller
What is allowed to change
What must not change
Verification plan
Rollback plan
Follow-up ratchet work
```

## Tests

Create:

```text
tests/change_plan/test_parser.py
tests/change_plan/test_validation.py
tests/change_plan/test_scope.py
```

## Acceptance Criteria

- Valid plan passes.
- Expired plan fails.
- Missing section fails.
- Out-of-plan path fails.
- Precommit passes.

---
