+++
id = "beta7-release"
kind = "release"
status = "complete"
base_ref = "origin/main"
expires = 2026-08-15
allowed_paths = [
  ".agent-maintainer/change-plans/beta7-release.md",
  ".agent-maintainer/change-plans/owner-hardening-and-ci-acceleration.md",
  ".docsync/attestations/**",
  ".docsync/trace.yml",
  "CHANGELOG.md",
  "README.md",
  "docs/ROADMAP.md",
  "docs/releases/0.1.0b7.md",
  "docs/releases/README.md",
  "docs/upgrading-to-0.1.0b7.md",
  "pyproject.toml",
  "tests/packaging/test_package_metadata.py",
  "tests/packaging/test_public_docs.py",
  "tests/release/test_distribution_bundle.py",
  "tests/release/test_release_state.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 25
max_changed_lines = 1000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
+++

# Agent Maintainer 0.1.0b7 Release

## Why this change intentionally large

The version bump, candidate notes, upgrade guidance, DocSync evidence, and
release-contract tests form one auditable release candidate.

## Why this should not be split smaller

Splitting metadata from its public truth and tests would create commits that
disagree about which package version is being qualified.

## What allowed to change

Only 0.1.0b7 version metadata, candidate-facing documentation, DocSync evidence,
release-state contracts, and the plan transition from merged hardening work.

## What must not change

Do not change product behavior, compatibility surfaces, credentials,
environments, publishing policy, or verification thresholds. Do not claim a
published release until both package indexes and clean-install smokes pass.

## Verification plan

Run doctor, precommit, full, CI, security, manual, and release-check profiles on
the exact release commit. Require hosted checks, then TestPyPI publication and a
clean TestPyPI smoke before tagging or publishing to PyPI.

## Rollback plan

Before publication, revert the release commit. After publication, preserve the
immutable beta and issue a later corrective version instead of replacing it.

## Follow-up ratchet work

Replace candidate-only prose with immutable commit, workflow, artifact, and
clean-install evidence after the package-index release completes.
