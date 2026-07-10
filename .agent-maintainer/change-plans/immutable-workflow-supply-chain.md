+++
id = "immutable-workflow-supply-chain"
kind = "release-hardening"
status = "active"
base_ref = "e3a7a23"
expires = 2026-08-31
allowed_paths = [
  ".agent-maintainer/change-plans/deep-release-evidence.md",
  ".agent-maintainer/change-plans/immutable-workflow-supply-chain.md",
  ".docsync/attestations/**",
  ".github/workflows/deep-verify.yml",
  ".github/workflows/publish.yml",
  ".github/workflows/verify.yml",
  "CHANGELOG.md",
  "docs/architecture/decisions/**",
  "docs/release-checklist.md",
  "docs/roadmap/critical-stabilization.md",
  "justfile",
  "pyproject.toml",
  "src/agent_maintainer/catalogs/global_checks.py",
  "src/agent_maintainer/release_artifacts.py",
  "src/agent_maintainer/release_artifacts_io.py",
  "src/agent_run_artifacts/distribution_bundle.py",
  "src/agent_run_artifacts/tach.domain.toml",
  "tach.toml",
  "tests/catalogs/test_config_catalog.py",
  "tests/packaging/test_github_actions_policy.py",
  "tests/packaging/test_publish_workflow.py",
  "tests/release/**",
  "zizmor.yml",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 45
max_changed_lines = 5000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = ["src/agent_run_artifacts/distribution_bundle.py"]
+++

# Immutable Workflow Supply Chain

## Why this change intentionally large

CS-08 binds workflow source identity to the distribution bytes that cross job
boundaries. Full-SHA action pinning alone does not detect a substituted package,
and a package digest without consumer-side verification does not gate publish.

## Why this should not be split smaller

The implementation may land in focused commits, but the unit closes only when
workflow pinning, concurrency, strict validation, bundle creation, transfer
verification, and publish-time verification enforce one continuous contract.

## What allowed to change

Change only workflow security policy, the distribution-bundle manifest and CLI,
publish wiring, focused regression tests, and the architecture, release, roadmap,
and changelog text needed to state the resulting contract.

## What must not change

Do not publish, change credentials or environments, weaken any verification
profile, accept tag-pinned actions, trust GitHub artifact names as content
identity, or let publish consume packages outside the verified bundle.

## Verification plan

Test missing, extra, symlinked, malformed, wrong-commit, wrong-size, and
digest-mismatched bundle contents. Prove every workflow action is full-SHA pinned
with a matching update comment; validate all workflows with Actionlint, schema,
Yamllint, and strict Zizmor; then run focused, precommit, CI, security, and full
profiles as applicable.

## Follow-up ratchet work

Keep the bundle validator fresh-strict and mutation-test candidate quality high;
future package types must add explicit allowlisted suffix and smoke coverage
before they can enter a release bundle.

## Rollback plan

Revert the CS-08 commits together. Do not retain a publish path that validates
only some transferred artifacts or only some publish jobs.
