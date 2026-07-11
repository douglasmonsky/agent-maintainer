+++
id = "pyright-strict-test-burndown"
kind = "mechanical-migration"
status = "active"
base_ref = "origin/main"
expires = 2026-07-25
allowed_paths = [
  ".agent-maintainer/change-plans/pyright-strict-production-burndown.md",
  ".agent-maintainer/change-plans/pyright-strict-test-burndown.md",
  "config/pyright-strict-baseline.json",
  "tests/doctor/test_doctor_commands.py",
  "tests/doctor/test_doctor_support_environment.py",
  "tests/hooks/test_hook_cli.py",
  "tests/hooks/test_hook_runtime.py",
  "tests/packaging/test_bootstrap_hooks.py",
  "tests/runners/test_secret_scan_runner.py",
  "tests/wait/test_wait_cli_register_identity.py",
]
forbidden_paths = ["src/**", "config/prod/**", ".env", ".env.*"]
max_changed_files = 16
max_changed_lines = 1500
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = [
  "tests/doctor/test_doctor_commands.py",
  "tests/doctor/test_doctor_support_environment.py",
  "tests/hooks/test_hook_cli.py",
  "tests/hooks/test_hook_runtime.py",
  "tests/packaging/test_bootstrap_hooks.py",
  "tests/runners/test_secret_scan_runner.py",
  "tests/wait/test_wait_cli_register_identity.py",
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
