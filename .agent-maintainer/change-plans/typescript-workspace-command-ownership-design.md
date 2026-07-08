+++
id = "typescript-workspace-command-ownership-design"
kind = "docs"
status = "active"
base_ref = "origin/main"
expires = 2026-07-22
allowed_paths = [
    ".agent-maintainer/change-plans/**",
    ".docsync/attestations/**",
    ".docsync/trace.yml",
    "docs/case-studies/typescript-provider-maturation.md",
    "docs/roadmap/full-roadmap-blueprint.md",
    "docs/roadmap/phases/phase-172-typescript-setup-advisor-root-package-boundary.md",
    "docs/roadmap/phases/phase-173-typescript-workspace-command-ownership-design.md",
    "docs/setup-advisor.md",
    "docs/typescript-javascript-provider.md",
    "tests/docs/test_first_touch_docs.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 12
max_changed_lines = 230
allow_source_without_test_change = true
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: typescript-workspace-command-ownership-design

## Why this change intentionally large

Phase 173 documents workspace command ownership semantics before any recursive
package discovery work, keeping provider docs, setup-advisor docs, phrase tests,
roadmap, and DocSync trace aligned.

## Why this should not be split smaller

The docs and tests describe one design boundary: root commands are valid only
when they intentionally cover the package surface being verified.

## What allowed to change

Only public TypeScript/setup-advisor docs, public-doc phrase tests, roadmap
Phase 172/173 docs, DocSync trace, and change-plan records may change.

## What must not change

Do not implement recursive package discovery, infer workspace managers, inspect
command bodies, add package ownership schema, or promote TypeScript gates to
blocking.

## Verification plan

Run public-doc phrase tests, DocSync check, roadmap docs tests, markdownlint on
touched docs, Tach, change-plan validation, and precommit verifier before
opening PR.

## Rollback plan

Revert branch remove workspace command ownership wording, Phase 173 roadmap
records, and phrase-test additions.

## Follow-up ratchet work

Design a concrete package ownership data model before any recursive workspace
setup-advisor recommendations.
