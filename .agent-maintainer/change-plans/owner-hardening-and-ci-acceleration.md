+++
id = "owner-hardening-and-ci-acceleration"
kind = "architecture-hardening"
status = "active"
base_ref = "origin/main"
expires = 2026-09-15
allowed_paths = [
  ".pre-commit-config.yaml",
  ".agent-maintainer/change-plans/owner-hardening-and-ci-acceleration.md",
  ".docsync/trace.yml",
  ".github/actions/**",
  ".github/workflows/deep-verify.yml",
  ".github/workflows/publish.yml",
  ".github/workflows/verify.yml",
  "AGENTS.agent-maintainer.md",
  "CHANGELOG.md",
  "README.md",
  "config/**",
  "docs/architecture/subsystem-stability.md",
  "docs/architecture/decisions/**",
  "docs/compatibility-shims.md",
  "docs/release-checklist.md",
  "docs/superpowers/plans/2026-07-15-owner-hardening-and-ci-acceleration.md",
  "docs/superpowers/specs/2026-07-15-owner-hardening-and-ci-acceleration-design.md",
  "docs/test-intelligence.md",
  "pyproject.toml",
  "src/agent_maintainer/**",
  "src/agent_repair_facts/**",
  "src/agent_run_artifacts/**",
  "src/agent_waits/**",
  "tach.toml",
  "tests/**",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 80
max_changed_lines = 8000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = [
  "src/agent_run_artifacts/release_evidence_validation.py",
  "src/agent_maintainer/verify/run_steps.py",
]
+++

# Owner Hardening and CI Acceleration

## Why this change intentionally large

The work closes one owner-facing reliability and speed program: policy
consistency, actionable worktree diagnostics, real contract smokes, safe
workflow caching, parallel release evidence, verifier-native aggregation,
faster local commits, and deletion of bounded compatibility facades.

## Why this should not be split smaller

Each behavior lands in a focused tested commit, but later speed work depends on
the earlier contract tests and aggregation boundaries. The branch remains one
review unit so CI and local execution semantics can be compared end to end.

## What allowed to change

Only verification policy, doctor diagnostics, safe artifact cleanup, structured
repair facts, contract tests, CI/release workflows, verifier grouping and
aggregation, local hook profile behavior, stability documentation, and
repository-owned compatibility facades proven unused.

## What must not change

Do not publish, change credentials or environments, weaken coverage or security
thresholds, accept unverified cached binaries, replace the authoritative
aggregate verification result, add compatibility shims, or delete a public
facade without proving repository consumers have migrated.

## Verification plan

Use test-first focused checks for every behavior. Run the CI-equivalent profile
after workflow and verifier changes, security/manual profiles when their gates
change, clean-environment contract smokes, and one final full profile. Compare
sequential and aggregated verification outcomes on passing and failing
fixtures.

## Follow-up ratchet work

Retain exact-SHA aggregation and fingerprint validation as mutation-test
candidates. Any new verification group or cached external tool must extend the
same fail-closed contract tests before entering a protected workflow.

## Rollback plan

Revert focused commits in reverse order. Release publication remains gated by
both exact-SHA aggregate evidence and the verified distribution bundle at every
intermediate state.
