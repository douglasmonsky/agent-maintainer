+++
id = "release-0.1.0b12-publication-evidence"
kind = "release"
status = "complete"
base_ref = "9dffc112"
expires = 2026-08-02
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  ".agent-maintainer/contracts-baseline.json",
  ".docsync/**",
  "CHANGELOG.md",
  "README.md",
  "config/dev-lock.txt",
  "docs/ROADMAP.md",
  "docs/releases/**",
  "docs/roadmap/cpp-cmake-experimental-provider-roadmap.md",
  "docs/roadmap/phases/phase-187-cpp-classification-config-registry-doctor.md",
  "docs/upgrading-to-0.1.0b12.md",
  "docs/upgrading-to-0.1.0b13.md",
  "pyproject.toml",
  "tests/packaging/test_package_metadata.py",
  "tests/packaging/test_public_docs.py",
  "tests/release/test_distribution_bundle.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 35
max_changed_lines = 1400
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: release-0.1.0b12-publication-evidence

## Why this change intentionally large

Recording a published beta touches package version metadata, immutable artifact
evidence, public latest-version pointers, upgrade guidance, roadmap state,
DocSync claims, release-state fixtures, and the next truthful candidate record.

## Why this should not be split smaller

The repository release contract requires the published evidence and next
candidate state to agree in one reviewed branch. Splitting them would leave
either false public publication claims or a published version as the active
development candidate, both of which the release-state checks reject.

## What allowed to change

Only b12 publication evidence, Phase 187 completion records, b12 and b13
adoption records, package and contract-baseline version metadata, directly
coupled release fixtures, DocSync traceability records, and this plan may
change.

## What must not change

Do not alter runtime behavior, dependencies, publishing workflows, package
artifacts, the immutable b12 tag, release assets, or package-index state. Do not
claim b13 features or publication evidence that do not exist.

## Verification plan

Validate focused release state, package metadata, distribution bundles,
contract compatibility, DocSync, release-only clean-environment packaging, and
a fresh full verifier. Then require every protected PR check before merging the
evidence update.

## Rollback plan

Revert only the evidence and next-candidate commit if its documentation is
incorrect. The published b12 artifacts and immutable tag remain intact;
correct publication records forward rather than rewriting package history.

## Follow-up ratchet work

This plan is complete when the evidence branch is coherent and ready for its
protected PR. Keep b13 intent-only until a separately approved roadmap slice is
implemented and verified.
