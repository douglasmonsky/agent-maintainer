+++
id = "repair-fact-pylint-vulture"
kind = "fix"
status = "complete"
base_ref = "origin/main"
expires = 2026-07-21
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  "src/agent_repair_facts/parsers/logs.py",
  "src/agent_repair_facts/registry.py",
  "tests/context/test_exact_facts.py",
  "tests/context/test_log_exact_facts.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 6
max_changed_lines = 400
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: repair-fact-pylint-vulture

## Why this change intentionally large

This branch expands exact repair facts for two existing Python checks whose
failures otherwise fall back to generic "failed with exit code" messages.

## Why this should not be split smaller

The Pylint and Vulture parsers are both small log-only additions to the same
repair-fact dispatch surface and share one focused regression suite.

## What allowed to change

Only repair-fact log parser dispatch, exact-facts regression tests, and
change-plan records may change.

## What must not change

Do not change verifier command behavior, add new check dependencies, change
thresholds, or alter context-pack rendering beyond the normalized facts already
produced by the parser registry.

## Verification plan

Run focused exact-facts tests, Ruff on touched Python files, `git diff --check`,
and broad CI before merging.

## Rollback plan

Revert this branch to restore generic repair facts for Pylint and Vulture logs.

## Follow-up ratchet work

Later repair-fact coverage slices can add parsers for remaining weak checks once
observed failure logs show stable output patterns.
