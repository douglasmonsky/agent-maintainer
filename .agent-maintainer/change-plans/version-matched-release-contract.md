+++
id = "version-matched-release-contract"
kind = "release-readiness"
status = "active"
base_ref = "dffb90c"
expires = 2026-08-31
allowed_paths = [
  ".agent-maintainer/change-plans/version-matched-release-contract.md",
  ".docsync/attestations/**",
  ".github/CODEOWNERS",
  ".github/ISSUE_TEMPLATE/**",
  "CHANGELOG.md",
  "CODE_OF_CONDUCT.md",
  "CONTRIBUTING.md",
  "README.md",
  "SECURITY.md",
  "SUPPORT.md",
  "config/**",
  "docs/**",
  "pyproject.toml",
  "src/agent_maintainer/**",
  "tests/**",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 220
max_changed_lines = 12000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Version-Matched Release Contract

## Why this change intentionally large

CS-09 reconciles a public contract spread across package metadata, current and
historical documentation, release notes, roadmap links, governance documents,
dependency-risk records, onboarding fixtures, and built-artifact smoke tests.
The audit found both content drift and 67 mechanically broken local links.

## Why this should not be split smaller

The work will land in focused commits, but CS-09 is complete only when the
version, changelog, public docs, release notes, upgrade guidance, package bytes,
local links, support policy, and release-readiness tests describe one beta.

## What allowed to change

Change only the public release contract, its generated/currentness checks,
realistic downstream fixtures, dependency-risk and governance records, and the
tests needed to prove them. Mechanical link repairs may touch archived roadmap
documents but must not rewrite their historical decisions.

## What must not change

Do not publish, tag, push, change external repository settings, invent completed
release evidence, weaken supported-version checks, or turn historical release
notes into descriptions of unreleased behavior.

## Verification plan

Run repository-wide Markdown link validation; version/changelog/release-state
tests; build/metadata/twine/extras checks; built-wheel and sdist smoke for all
advertised console scripts; realistic existing-application onboarding fixtures;
precommit, full or CI as appropriate, manual, security, and release profiles;
then independently review the public/package contract.

## Follow-up ratchet work

Every user-facing merge must update Unreleased, and every future release must
add versioned release notes plus executable built-artifact evidence before the
published-version pointer moves.

## Rollback plan

Revert the CS-09 commits together. Never retain a version bump whose package,
release notes, changelog, or public documentation failed the same-commit matrix.
