+++
id = "critical-stabilization"
kind = "integration-branch-series"
status = "active"
base_ref = "origin/main"
integration_branch = "codex/critical-stabilization"
target_branch = "main"
merge_strategy = "squash-after-series"
expected_units = [
  "record the stabilization contract",
  "constrain MCP and DocSync filesystem access",
  "unify managed hooks and make mutations lossless and idempotent",
  "validate configuration before constructing behavior",
  "make detached verification own its process lifecycle",
  "restore deep verification and immutable release evidence",
  "reconcile changelog documentation and built-package behavior",
]
expires = 2026-08-31
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  ".claude/**",
  ".codex/**",
  ".docsync/**",
  ".github/**",
  ".gitignore",
  "CHANGELOG.md",
  "CONTRIBUTING.md",
  "README.md",
  "SECURITY.md",
  "SUPPORT.md",
  "UPGRADING.md",
  "config/**",
  "docs/**",
  "examples/**",
  "justfile",
  "pyproject.toml",
  "scripts/**",
  "src/**",
  "tach.toml",
  "tests/**",
  "uv.lock",
  "zizmor.yml",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 200
max_changed_lines = 20000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: critical-stabilization

## Why this change intentionally large

The deep audit found interacting release-blocking failures across filesystem
boundaries, generated hooks, mutation semantics, configuration, background
processes, and release evidence. The branch needs a visible integration contract
because the complete repair necessarily crosses several otherwise independent
packages, workflows, tests, and public documents.

## Why this should not be split smaller

The implementation is split into focused commits and verification units, but
the repository is not release-ready until the units work together. Keeping one
integration branch and one acceptance roadmap prevents a partial filesystem or
workflow repair from being mistaken for completion while preserving reviewable
commit boundaries.

## What allowed to change

Only the paths listed in front matter may change. Changes must directly satisfy
an outcome in `docs/roadmap/critical-stabilization.md`, add its regression
evidence, update generated artifacts, or reconcile the public release contract.
Source-bearing commits must include focused tests.

## What must not change

Do not add unrelated features, new ecosystems, production configuration,
credentials, deployment behavior, billing, account permissions, or broad
framework replacements. Do not lower quality thresholds, discard user hooks or
files, expose unsafe local path behavior through MCP, or publish a release from
this branch.

## Verification plan

Run focused failure-mode tests for each unit, then the affected formatting,
lint, typing, architecture, generated-currentness, and security checks. Run full
verification for every source-bearing unit. Before completion, run full, CI,
security, manual, and release profiles against one commit, validate workflows,
scan the final diff for secrets and private data, and independently review the
complete branch diff.

## Rollback plan

Each implementation unit is a focused Conventional Commit and can be reverted
without rewriting history. Preserve the initial roadmap commit so an incomplete
rollback still records open risks. Do not restore an unsafe behavior merely for
compatibility; if a unit must be backed out, disable or clearly quarantine the
affected preview surface until a corrected patch is ready.

## Follow-up ratchet work

After stabilization, keep path-policy, mutation-idempotency, generated-file,
configuration-schema, terminal-close, workflow-integrity, documentation-link,
and built-package smoke tests in required CI. Measure external activation and
repair outcomes before promoting labs surfaces or resuming feature expansion.
