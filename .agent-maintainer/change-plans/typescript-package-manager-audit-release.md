+++
id = "typescript-package-manager-audit-release"
kind = "feat"
status = "active"
base_ref = "origin/main"
expires = 2026-08-03
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  ".agent-maintainer/contracts-baseline.json",
  ".docsync/**",
  "CHANGELOG.md",
  "README.md",
  "config/**",
  "docs/**",
  "pyproject.toml",
  "src/**",
  "tests/**",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 100
max_changed_lines = 4500
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: typescript-package-manager-audit-release

## Why this change intentionally large
This release slice completes the TypeScript package-manager audit capability
across configuration, normalized repair facts, provider/reporting plumbing,
fixtures, tests, architecture metadata, public documentation, and the b14
release contract. The existing branch contains the preceding parser and
contract ratchets that make this end-to-end evidence coherent.

## Why this should not be split smaller
Parser support without provider and artifact propagation would lose manager
identity; implementation without pinned fixtures and docs would be unreviewable
and drift-prone. The release metadata and DocSync attestations must land with
the behavior they describe so the b14 candidate is reproducible.

## What allowed to change
Only the TypeScript audit implementation and its existing configuration,
registry, artifact, verification, fixture, test, architecture, roadmap,
release-documentation, and DocSync surfaces may change. The plan scope also
allows this plan record itself and the version/release metadata needed for b14.

## What must not change
Do not execute npm, pnpm, Yarn, or Bun commands; infer package-manager state;
relax coverage, typing, security, or architecture thresholds; modify production
configuration or credentials; or add unrelated ecosystem behavior. Publishing
must use the repository's existing trusted GitHub Release workflow.

## Verification plan
Run focused parser, provider, configuration, exact-fact, artifact, packaging,
and documentation tests; DocSync; change-plan validation; the full verifier;
and the release-check gate. CI must pass both tests-and-coverage and
static-and-policy groups before merge, followed by the trusted PyPI workflow.

## Rollback plan
Revert the b14 merge commit and release tag, then remove the package-manager
audit parser, adapters, configuration fields, fixtures, docs, and attestations
as one bounded unit. Do not rewrite history or force-push.

## Follow-up ratchet work
After publication, record the tag, merge SHA, workflow run, and artifact
digests in the b14 evidence document, then open the next candidate version for
the following TypeScript roadmap phase. Keep package-manager audit checks
advisory until their evidence supports a later policy decision.
