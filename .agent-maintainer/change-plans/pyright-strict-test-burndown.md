+++
id = "pyright-strict-test-burndown"
kind = "mechanical-migration"
status = "complete"
base_ref = "origin/main"
expires = 2026-07-25
allowed_paths = [
  ".agent-maintainer/change-plans/pyright-strict-production-burndown.md",
  ".agent-maintainer/change-plans/pyright-strict-test-burndown.md",
  ".docsync/attestations/**",
  "config/pyright-strict-baseline.json",
  "tests/**",
]
forbidden_paths = ["src/**", "config/prod/**", ".env", ".env.*"]
max_changed_files = 40
max_changed_lines = 1500
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = ["tests/**"]
+++
# Cohesive Change Plan: pyright-strict-test-burndown

## Why this change intentionally large

Production source and tests are strict-clean. Four cohesive test batches removed
292 diagnostics, including the final 77-diagnostic batch, by replacing untyped
callbacks, narrowing structured values, and testing public behavior instead of
private implementation seams.

## Why this should not be split smaller

The selected modules shared mechanical callback and structured-value patterns.
Keeping each batch cohesive avoided repeating baseline, full-verifier, and
hosted-CI work without reducing implementation risk.

## What allowed to change

Only this plan, the completed production plan, the strict baseline, and tests
changed. Production interfaces remained unchanged.

## What must not change

Do not modify production source, dependencies, workflows, release configuration,
global strictness, or verifier thresholds. Do not add type suppressions,
unchecked casts, or permissive `Any` annotations.

## Verification plan

Run mapped tests, Ruff, exact strict Pyright, change-plan validation, and one
full local verifier. Merge only after Python 3.11–3.14, CodeQL, hosted
verification, and review state are clean.

## Rollback plan

Revert the single migration commit. The reviewed strict baseline preserves the
exact pre-batch diagnostic state.

## Follow-up ratchet work

The strict baseline reached zero. Remove the now-obsolete ratchet artifact and
close the strict-typing roadmap item in the follow-up cleanup.
