+++
id = "doctor-consumer-repo-root"
kind = "fix"
status = "complete"
base_ref = "origin/main"
expires = 2026-07-23
allowed_paths = [
  ".agent-maintainer/change-plans/codex-terminal-rewake-hardening.md",
  ".agent-maintainer/change-plans/doctor-consumer-repo-root.md",
  "docs/tool-map.md",
  "src/agent_maintainer/config/loader.py",
  "src/agent_maintainer/core/bootstrap.py",
  "src/agent_maintainer/doctor/cli.py",
  "tests/config/test_config_loader_roots.py",
  "tests/config/test_config_loading.py",
  "src/agent_maintainer/doctor/support/environment.py",
  "tests/doctor/test_doctor.py",
  "tests/doctor/test_doctor_cli_output.py",
  "tests/doctor/test_doctor_support_environment.py",
  "tests/packaging/test_bootstrap_install.py",
  "tests/packaging/test_bootstrap_paths.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 12
max_changed_lines = 360
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: doctor-consumer-repo-root

## Why this change intentionally large

This is a small upstream doctor fix plus tests. It also retires the completed
Codex terminal-rewake change plan so this focused branch can validate against
the correct scope.

## Why this should not be split smaller

The doctor root predicate and regression tests need to land together; otherwise
consumer repos can still fail `doctor` for lacking agent-maintainer source.

## What allowed to change

Only the doctor repo-root check, focused doctor tests, and the two change-plan
records listed in `allowed_paths`.

## What must not change

Do not change verifier thresholds, install behavior, hook behavior, package
layout, wait orchestration, external integrations, credentials, or production
configuration.

## Verification plan

Run focused doctor tests, a disposable consumer-repo `doctor` smoke, Ruff,
Pyright, Tach, DocSync, `git diff --check`, and the precommit verifier.

## Rollback plan

Revert this branch to restore the previous agent-maintainer-source repo-root
requirement and the prior change-plan statuses.

## Follow-up ratchet work

Consider documenting `doctor` as package-first consumer tooling if more
deployment repos hit setup-health ambiguity.
