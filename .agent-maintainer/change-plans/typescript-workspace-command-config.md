+++
id = "typescript-workspace-command-config"
kind = "test"
status = "active"
base_ref = "origin/main"
expires = 2026-07-22
allowed_paths = [
    ".agent-maintainer/change-plans/**",
    ".docsync/attestations/**",
    ".docsync/trace.yml",
    "docs/roadmap/full-roadmap-blueprint.md",
    "docs/roadmap/phases/phase-173-typescript-workspace-command-ownership-design.md",
    "docs/roadmap/phases/phase-174-typescript-workspace-command-config.md",
    "docs/setup-advisor.md",
    "docs/typescript-javascript-provider.md",
    "src/agent_maintainer/config/coercion.py",
    "src/agent_maintainer/config/workspaces.py",
    "src/agent_maintainer/ecosystems/typescript/provider.py",
    "tests/catalogs/test_typescript_catalog.py",
    "tests/config/test_workspace_config.py",
    "tests/docs/test_first_touch_docs.py",
    "tests/docs/test_roadmap_docs.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 18
max_changed_lines = 260
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: typescript-workspace-command-config

## Why this change intentionally large

Phase 174 adds one public configuration surface for explicit workspace-owned
TypeScript commands and keeps the implementation, tests, docs, roadmap, and
change-plan state aligned.

## Why this should not be split smaller

Loading workspace TypeScript commands without emitting checks would create dead
configuration, while emitting checks without docs would hide the ownership
contract.

## What allowed to change

Only workspace config coercion/model code, TypeScript provider check generation,
focused config/catalog/docs tests, roadmap index guard maintenance, public
TypeScript/setup-advisor docs, roadmap records, DocSync trace/attestations, and
change-plan records may change.

## What must not change

Do not scan nested package files, infer workspace managers, parse package
scripts, add workspace-specific profile matrices, or make TypeScript gates
blocking.

## Verification plan

Run focused workspace config, TypeScript catalog, public-doc phrase, DocSync,
Tach, change-plan, markdownlint, diff, and precommit verifier checks before
opening PR.

## Rollback plan

Revert the branch to remove workspace TypeScript command fields, generated
workspace check names, Phase 174 docs, and phrase-test additions.

## Follow-up ratchet work

Add setup-advisor examples for explicit workspace command ownership after this
configuration surface is stable.
