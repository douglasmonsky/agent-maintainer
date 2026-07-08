+++
id = "typescript-react-roadmap"
kind = "docs"
status = "complete"
base_ref = "origin/main"
expires = 2026-07-21
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  "docs/ROADMAP.md",
  "docs/roadmap/polyglot-ecosystem-providers.md",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 6
max_changed_lines = 400
allow_source_without_test_change = true
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: typescript-react-roadmap

## Why this change intentionally large

This branch updates the roadmap direction after renewed user prioritization of
polyglot work, specifically TypeScript and React provider maturation.

## Why this should not be split smaller

The active roadmap and the polyglot provider roadmap need to change together so
the implementation tracker and provider strategy stay consistent.

## What allowed to change

Only roadmap documentation and change-plan records may change in this docs-only
planning branch.

## What must not change

Do not add provider runtime behavior, new ecosystem support, CI changes,
credentials, production configuration, or broad repository structure.

## Verification plan

Run roadmap documentation tests, DocSync check, `git diff --check`, and GitHub
CI for the PR.

## Rollback plan

Revert this branch's roadmap commit and change-plan commit to return the roadmap
to the previous Future Work wording.

## Follow-up ratchet work

No ratchet baseline updates are expected. The next implementation PR should
start Phase 165 with React fixture corpus work.
