+++
id = "pyright-strict-test-burndown"
kind = "mechanical-migration"
status = "active"
base_ref = "origin/main"
expires = 2026-07-25
allowed_paths = [
  ".agent-maintainer/change-plans/pyright-strict-production-burndown.md",
  ".agent-maintainer/change-plans/pyright-strict-test-burndown.md",
  ".docsync/attestations/**",
  "config/pyright-strict-baseline.json",
  "tests/archguard/test_git_diff.py",
  "tests/attention/test_attention_signals.py",
  "tests/checks/test_change_budget_relevance.py",
  "tests/checks/test_file_lengths.py",
  "tests/context/test_compression.py",
  "tests/context/test_pack_compression.py",
  "tests/core/test_command_run.py",
  "tests/core/test_structured_artifact_summaries.py",
  "tests/docsync/test_freshness.py",
  "tests/hooks/test_hook_manager.py",
  "tests/hooks/test_pr_wait_hook.py",
  "tests/packaging/test_initializer.py",
  "tests/verify/test_git_refs.py",
  "tests/verify/test_run_steps.py",
]
forbidden_paths = ["src/**", "config/prod/**", ".env", ".env.*"]
max_changed_files = 20
max_changed_lines = 1500
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = [
  "tests/archguard/test_git_diff.py",
  "tests/attention/test_attention_signals.py",
  "tests/checks/test_change_budget_relevance.py",
  "tests/checks/test_file_lengths.py",
  "tests/context/test_compression.py",
  "tests/context/test_pack_compression.py",
  "tests/core/test_command_run.py",
  "tests/core/test_structured_artifact_summaries.py",
  "tests/docsync/test_freshness.py",
  "tests/hooks/test_hook_manager.py",
  "tests/hooks/test_pr_wait_hook.py",
  "tests/packaging/test_initializer.py",
  "tests/verify/test_git_refs.py",
  "tests/verify/test_run_steps.py",
]
+++
# Cohesive Change Plan: pyright-strict-test-burndown

## Why this change intentionally large

Production source is strict-clean. The remaining strict diagnostics are test
typing debt, primarily repeated untyped monkeypatch lambdas and intentional
access to private test seams. Batches should remove 50–80 diagnostics at a time
by shared fixture pattern and package risk.

## Why this should not be split smaller

The selected modules share one mechanical callback-typing pattern and form a
60–80 diagnostic batch. Splitting them would repeat the same review, baseline, full
verifier, and hosted-CI work without reducing implementation risk.

## What allowed to change

Only this plan, the completed production plan, the strict baseline, and the
listed test modules may change in this batch. Test behavior and production
interfaces must remain unchanged.

## What must not change

Do not modify production source, dependencies, workflows, release configuration,
global strictness, or verifier thresholds. Do not add type suppressions,
unchecked casts, or permissive `Any` annotations.

## Verification plan

Run the six mapped test modules, Ruff, Flake8 where applicable, exact strict
Pyright, change-plan validation, and one full local verifier. Merge only after
Python 3.11–3.14, CodeQL, hosted verification, and review state are clean.

## Rollback plan

Revert the single migration commit. The reviewed strict baseline preserves the
exact pre-batch diagnostic state.

## Follow-up ratchet work

Continue test-only batches of 50–80 diagnostics grouped by package and fixture
pattern until the baseline reaches zero, then remove the ratchet artifact and
close the strict-typing roadmap item.
