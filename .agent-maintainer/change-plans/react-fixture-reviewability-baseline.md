+++
id = "react-fixture-reviewability-baseline"
kind = "feat"
status = "complete"
base_ref = "origin/main"
expires = 2026-07-22
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  "tests/assess/test_typescript_real_repo_reviewability.py",
  "docs/roadmap/full-roadmap-blueprint.md",
  "docs/roadmap/phases/phase-165-react-fixture-corpus-and-reviewability-baseline.md",
  "docs/ROADMAP.md",
  "docs/case-studies/typescript-provider-maturation.md",
  ".docsync/trace.yml",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 8
max_changed_lines = 450
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: react-fixture-reviewability-baseline

## Why this change intentionally large

This branch implements Phase 165 by adding React-shaped TypeScript
reviewability evidence and the missing split phase spec.

## Why this should not be split smaller

The fixture, roadmap phase spec, roadmap index, and maturation notes need to
change together so the implementation has a durable source of truth.

## What allowed to change

Only the React reviewability evidence test, roadmap/docs references, DocSync
trace wording if needed, and change-plan records may change.

## What must not change

Do not add package-manager autodetection, execute Node tools, promote
TypeScript/React to blocking status, or change provider runtime behavior.

## Verification plan

Run focused TypeScript reviewability tests, DocSync public trace tests,
DocSync check, Ruff on touched Python tests, `git diff --check`, and CI before
merging.

## Rollback plan

Revert this branch to remove the React evidence baseline and Phase 165 spec.

## Follow-up ratchet work

Phase 166 should add package-manager and workspace evidence before considering
TypeScript/React setup guidance or blocking gates.
