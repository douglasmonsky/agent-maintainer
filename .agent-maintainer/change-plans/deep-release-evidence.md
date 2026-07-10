+++
id = "deep-release-evidence"
kind = "release-hardening"
status = "active"
base_ref = "7733599"
expires = 2026-08-31
allowed_paths = [
  ".agent-maintainer/change-plans/deep-release-evidence.md",
  ".github/workflows/deep-verify.yml",
  ".github/workflows/publish.yml",
  ".github/workflows/verify.yml",
  "CHANGELOG.md",
  "config/pyright-strict-baseline.json",
  "docs/architecture/decisions/**",
  "docs/configuration-reference.md",
  "docs/release-checklist.md",
  "docs/roadmap/critical-stabilization.md",
  "justfile",
  "pyproject.toml",
  "src/agent_maintainer/assess/cli.py",
  "src/agent_maintainer/assess/tach.domain.toml",
  "src/agent_maintainer/change_plan/parser.py",
  "src/agent_maintainer/core/artifact_environment.py",
  "src/agent_maintainer/release_evidence.py",
  "src/agent_maintainer/runners/mutmut_lock.py",
  "src/agent_maintainer/runners/pyright.py",
  "src/agent_maintainer/runners/pyright_strict.py",
  "src/agent_maintainer/runners/pyright_strict_baseline.py",
  "src/agent_maintainer/runners/tach.domain.toml",
  "src/agent_maintainer/test_intel/coverage.py",
  "src/agent_run_artifacts/release_evidence.py",
  "src/agent_run_artifacts/tach.domain.toml",
  "tach.toml",
  "tests/config/test_config_validation.py",
  "tests/attention/test_attention_cli.py",
  "tests/checks/test_mutmut_targets.py",
  "tests/context/test_logs.py",
  "tests/core/test_guidance.py",
  "tests/ratchet/test_status.py",
  "tests/release/**",
  "tests/runners/test_mutmut_runner.py",
  "tests/runners/test_pyright_strict.py",
  "tests/runners/test_pyright_strict_baseline.py",
  "tests/runtime_events/test_runtime_event_export.py",
  "tests/scoring/test_scoring_dataset.py",
  "tests/packaging/test_publish_workflow.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 60
max_changed_lines = 7000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = ["src/agent_maintainer/runners/pyright_strict.py"]
+++
# Cohesive Change Plan: deep-release-evidence

## Why this change intentionally large

CS-07 joins two release-trust boundaries: the manual profile must enforce a
reviewed strict-typing debt ratchet, and publishing must accept evidence only
when every required profile passed for one clean, exact commit. Either boundary
alone would still allow a release from partial or substitutable evidence.

## Why this should not be split smaller

The work lands in focused commits for strict typing and exact-commit release
evidence. The branch closes only when CI preserves and aggregates the profile
manifests that the publish workflow validates. Splitting the workflow from its
validator would temporarily create an unenforced trust claim.

## What allowed to change

Change only the strict-Pyright runner and reviewed baseline, focused genuine
strict defects, exact-commit release-evidence code, the required-profile CI and
publish wiring, their tests and architecture contracts, and the roadmap,
checklist, ADR, and changelog text needed to state the resulting behavior.

## What must not change

Do not weaken normal verification, treat total error count as sufficient,
silence new diagnostics through broad ignores, accept dirty or mixed-commit
manifests, publish from locally reconstructed evidence, or include the CS-08
action-pinning and transferred-artifact digest work in this unit.

## Verification plan

Add ratchet tests proving that new file/rule pairs and error substitution fail
even when the total falls. Run strict Pyright and the manual profile against a
reviewed versioned baseline. Add release-evidence tests for missing profiles,
failed checks, dirty worktrees, duplicate profiles, wrong commits, stale or
malformed manifests, and a passing exact-commit matrix. Validate workflow
contracts, run focused release and runner tests, then full, CI, security,
manual, release, and workflow-validation gates as applicable.

## Rollback plan

Keep the ratchet and release-evidence implementations in separate focused
commits. Revert a defective validator together with its workflow wiring; the
publish job must remain disabled or fail closed until corrected. Reverting the
baseline must also revert its file/rule comparison semantics.

## Follow-up ratchet work

CS-08 will pin every workflow action by full SHA, add build-produced artifact
digests verified after each transfer, and enforce strict workflow supply-chain
validation. Future strict-typing cleanup must lower individual file/rule
allowances rather than refreshing the baseline wholesale.
