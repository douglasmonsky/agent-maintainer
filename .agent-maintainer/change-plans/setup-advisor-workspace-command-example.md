+++
id = "setup-advisor-workspace-command-example"
kind = "docs"
status = "active"
base_ref = "origin/main"
expires = 2026-07-22
allowed_paths = [
    ".agent-maintainer/change-plans/**",
    ".docsync/attestations/**",
    ".docsync/trace.yml",
    "docs/roadmap/full-roadmap-blueprint.md",
    "docs/roadmap/phases/phase-174-typescript-workspace-command-config.md",
    "docs/roadmap/phases/phase-175-setup-advisor-workspace-command-example.md",
    "docs/setup-advisor.md",
    "src/agent_maintainer/assess/setup_advisor.py",
    "tests/assess/test_setup_advisor.py",
    "tests/docs/test_first_touch_docs.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 11
max_changed_lines = 180
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: setup-advisor-workspace-command-example

## Why this change intentionally large

Phase 175 teaches setup advisor output and docs to show explicit workspace
TypeScript command ownership now that the config surface exists.

## Why this should not be split smaller

The recommendation text, docs example, focused tests, roadmap, and DocSync trace
describe one user-facing setup-advisor example.

## What allowed to change

Only setup-advisor recommendation wording, setup-advisor docs, focused
setup-advisor and public-doc tests, roadmap records, DocSync trace/attestations,
and change-plan records may change.

## What must not change

Do not scan nested package files, infer workspace managers, parse package
scripts, change TypeScript provider runtime behavior, or promote TypeScript
gates to blocking.

## Verification plan

Run focused setup-advisor tests, public-doc phrase tests, DocSync, Tach,
change-plan, markdownlint, diff, and precommit verifier before opening PR.

## Rollback plan

Revert this branch to remove the workspace command example and restore previous
setup-advisor recommendation wording.

## Follow-up ratchet work

Add richer setup-advisor evidence for workspace manifests only after explicit
workspace command examples stay stable.
