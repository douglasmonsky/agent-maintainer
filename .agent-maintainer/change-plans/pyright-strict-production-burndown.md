+++
id = "pyright-strict-production-burndown"
kind = "mechanical-migration"
status = "active"
base_ref = "origin/main"
expires = 2026-07-25
allowed_paths = [
  ".agent-maintainer/change-plans/pyright-strict-production-burndown.md",
  "config/pyright-strict-baseline.json",
  "docs/architecture/decisions/**",
  "src/agent_maintainer/change_plan/**",
  "src/agent_maintainer/checks/**",
  "src/agent_maintainer/core/scaffold/**",
  "src/agent_maintainer/core/tach.domain.toml",
  "src/agent_maintainer/hooks/mutations.py",
  "tests/change_plan/**",
  "tests/checks/**",
  "tests/core/**",
  "tests/hooks/test_hook_mutations.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 32
max_changed_lines = 2500
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = [
  "src/agent_maintainer/core/scaffold/planning.py",
  "src/agent_maintainer/core/scaffold/transaction.py",
  "src/agent_maintainer/checks/file_lengths.py",
  "src/agent_maintainer/checks/cohesive_override.py",
  "src/agent_maintainer/checks/mutmut_targets.py",
  "src/agent_maintainer/change_plan/parser.py",
  "src/agent_maintainer/hooks/mutations.py",
]
+++
# Cohesive Change Plan: pyright-strict-production-burndown

## Why this change intentionally large

The remaining production strict-Pyright debt is a mechanical migration of
decoded structured values, collection factories, and public callback surfaces
across the repository's maintenance infrastructure. The same runtime-validation
pattern has already been proven in the preceding strict-burndown batches.

## Why this should not be split smaller

The source fixes, mapped tests, architecture contracts, baseline update, and
decision record form one reviewable type-safety migration. Splitting each small
module into a separate PR would repeatedly pay identical full-verifier and
hosted-CI costs while leaving the production ratchet partially migrated.

## What allowed to change

Only the listed change-plan file, strict baseline, architecture decisions,
targeted scaffold/check/change-plan/hook modules and their Tach contracts, and
mapped tests may change. Behavior changes are limited to rejecting malformed
non-JSON keys or values at existing external-data boundaries.

## What must not change

Do not change dependencies, release configuration, workflows, production data,
public visibility, global Pyright strictness, ordinary verifier thresholds, or
unrelated runtime behavior. Do not add suppressions, unchecked casts, or
permissive `Any` annotations.

## Verification plan

Use red-green boundary tests for any intentional malformed-input behavior. Run
mapped package tests first, then Ruff, Flake8, strict Pyright, Archguard, Tach,
DocSync when evidence changes, change-plan validation, and one full local
verifier. Publish a draft PR with the required cohesive-change explanation and
merge only after Python 3.11-3.14, CodeQL, full hosted verification, and review
state are clean.

## Rollback plan

Revert the single migration commit before merge. Each transformed module keeps
its pre-migration behavior for valid inputs, and the committed strict baseline
provides the exact diagnostic rollback point.

## Follow-up ratchet work

Continue the remaining production diagnostics in one final planned batch, then
run larger test-only batches. When strict diagnostics reach zero, remove the
baseline and mark the roadmap completion item.
