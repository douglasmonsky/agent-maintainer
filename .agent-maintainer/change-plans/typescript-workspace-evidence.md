+++
id = "typescript-workspace-evidence"
kind = "feat"
status = "active"
base_ref = "origin/main"
expires = 2026-07-22
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  "src/agent_maintainer/ecosystems/typescript/classification.py",
  "tests/assess/test_typescript_real_repo_reviewability.py",
  "docs/roadmap/full-roadmap-blueprint.md",
  "docs/roadmap/phases/phase-166-typescript-package-manager-and-workspace-evidence.md",
  "docs/ROADMAP.md",
  "docs/case-studies/typescript-provider-maturation.md",
  ".docsync/trace.yml",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 9
max_changed_lines = 450
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: typescript-workspace-evidence

## Why this change intentionally large

This branch implements Phase 166 by adding pnpm workspace-shaped TypeScript
reviewability evidence and the missing split phase spec.

## Why this should not be split smaller

The classifier gap, fixture, roadmap phase spec, roadmap index, maturation
notes, and DocSync trace need to change together so the evidence remains
durable and documented.

## What allowed to change

Only TypeScript workspace config classification, reviewability evidence tests,
roadmap/docs references, DocSync trace wording, and change-plan records may
change.

## What must not change

Do not add package-manager autodetection, execute Node tools, promote
TypeScript/React to blocking status, or add framework-specific generated-file
policy.

## Verification plan

Run focused TypeScript reviewability tests, DocSync public trace tests,
DocSync check, Ruff on touched Python files, `git diff --check`, and CI before
merging.

## Rollback plan

Revert this branch to remove the workspace evidence baseline and
`pnpm-workspace.yaml` classification.

## Follow-up ratchet work

Phase 167 should add React/Vite/Next structured test and coverage repair facts
without turning TypeScript/React gates blocking.
