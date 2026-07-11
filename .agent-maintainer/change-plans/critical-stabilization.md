+++
id = "critical-stabilization-foundations"
kind = "integration-branch-series"
status = "complete"
base_ref = "origin/main"
integration_branch = "codex/critical-stabilization"
target_branch = "main"
merge_strategy = "merge-after-tranche"
expected_units = [
  "record the stabilization contract",
  "constrain MCP and DocSync filesystem access",
  "unify managed hooks and make mutations lossless and idempotent",
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
# Cohesive Change Plan: critical-stabilization-foundations

## Why this change intentionally large

The deep audit found interacting release-blocking failures in filesystem
boundaries, generated hooks, and mutation semantics. This foundations tranche
needed one visible integration contract because safe onboarding depends on the
path boundary, executable inventory, merge policy, and rollback behavior working
together.

## Why this should not be split smaller

The implementation is split into focused commits, but CS-01 through CS-04 form
one reviewable trust boundary: repository-controlled reads are confined before
the generated installers and lifecycle commands are allowed to mutate files.
Later roadmap units use separate change plans and PRs so this merged foundation
does not leave an active branch-specific plan on `main`.

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
verification for every source-bearing unit, security verification for the path
boundary, clean-clone lifecycle tests, and a final secrets/private-data review.
The final stabilization PR retains the all-profile release-evidence gate.

## Rollback plan

Each implementation unit is a focused Conventional Commit and can be reverted
without rewriting history. Preserve the initial roadmap commit so an incomplete
rollback still records open risks. Do not restore an unsafe behavior merely for
compatibility; if a unit must be backed out, disable or clearly quarantine the
affected preview surface until a corrected patch is ready.

## Follow-up ratchet work

Continue the remaining roadmap through separate active plans for configuration,
detached verification, release evidence/workflow integrity, and public-package
reconciliation. After stabilization, keep each resulting ratchet in required CI
and measure external activation and repair outcomes before feature expansion.
