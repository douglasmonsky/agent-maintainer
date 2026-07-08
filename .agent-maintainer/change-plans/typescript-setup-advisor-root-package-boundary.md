+++
id = "typescript-setup-advisor-root-package-boundary"
kind = "test"
status = "active"
base_ref = "origin/main"
expires = 2026-07-22
allowed_paths = [
    ".agent-maintainer/change-plans/**",
    ".docsync/attestations/**",
    ".docsync/trace.yml",
    "docs/roadmap/full-roadmap-blueprint.md",
    "docs/roadmap/phases/phase-171-typescript-setup-advisor-script-fixtures.md",
    "docs/roadmap/phases/phase-172-typescript-setup-advisor-root-package-boundary.md",
    "docs/setup-advisor.md",
    "tests/assess/test_setup_advisor.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 10
max_changed_lines = 210
allow_source_without_test_change = true
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: typescript-setup-advisor-root-package-boundary

## Why this change intentionally large

Phase 172 codifies setup-advisor's current root-package TypeScript boundary
with focused tests, docs, roadmap, and DocSync trace in one advisory slice.

## Why this should not be split smaller

The test and docs need to land together so users do not infer monorepo package
ownership support from the Phase 171 script-shape examples.

## What allowed to change

Only setup-advisor tests, setup-advisor docs, Phase 171/172 roadmap docs,
DocSync trace or required attestations, and change-plan records may change.

## What must not change

Do not recursively scan nested package files, infer workspace managers, inspect
command bodies, introduce a command ownership model, or make TypeScript gates
blocking.

## Verification plan

Run focused setup-advisor tests, DocSync check, roadmap docs tests,
markdownlint on touched docs, Tach, change-plan validation, and precommit
verifier before opening PR.

## Rollback plan

Revert branch remove root-package boundary tests, docs wording, roadmap Phase
172, and DocSync wording.

## Follow-up ratchet work

Design workspace command ownership before adding recursive package discovery or
workspace-aware recommendations.
