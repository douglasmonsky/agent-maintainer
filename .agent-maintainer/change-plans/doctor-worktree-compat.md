+++
id = "doctor-worktree-compat"
kind = "fix"
status = "complete"
base_ref = "origin/main"
expires = 2026-07-21
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  ".docsync/trace.yml",
  "docs/change-plans.md",
  "docs/cohesive-change-plans.md",
  "src/agent_maintainer/change_plan/**",
  "src/agent_maintainer/doctor/setup.py",
  "tests/change_plan/**",
  "tests/checks/test_change_budget_plans.py",
  "tests/doctor/test_doctor_environment.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 12
max_changed_lines = 700
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: doctor-worktree-compat

## Why this change intentionally large

This branch fixes two linked repository-health failures found during roadmap
assessment: `doctor` crashed in linked worktrees, and a completed historical
change plan still blocked new focused branches.

## Why this should not be split smaller

The doctor fix needs the change-plan lifecycle cleanup to pass the repository
verifier without bypassing the change-budget gate. Keeping both edits together
keeps the health-gate behavior reviewable and avoids landing a branch that
requires a local override.

## What allowed to change

Only the doctor duplicate-artifact check, change-plan status validation, focused
tests, the active change-plan records, and the public change-plan status docs
may change.

## What must not change

Do not alter verifier thresholds, coverage gates, Tach contracts, production
configuration, credentials, broad source layout, or unrelated roadmap docs.

## Verification plan

Run targeted doctor, change-plan, and change-budget tests, then run the broad
`just v` verifier profile through the background wait path.

## Rollback plan

Revert this branch's commits to restore the previous single-active-plan-only
behavior and the prior doctor duplicate-artifact implementation.

## Follow-up ratchet work

No ratchet baseline updates are expected. Generated artifact hygiene remains the
next separate roadmap chunk.
