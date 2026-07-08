+++
id = "typescript-setup-advisor-script-fixtures"
kind = "test"
status = "complete"
base_ref = "origin/main"
expires = 2026-07-22
allowed_paths = [
    ".agent-maintainer/change-plans/**",
    ".docsync/attestations/**",
    ".docsync/trace.yml",
    "docs/roadmap/full-roadmap-blueprint.md",
    "docs/roadmap/phases/phase-170-typescript-setup-advisor-output-guidance.md",
    "docs/roadmap/phases/phase-171-typescript-setup-advisor-script-fixtures.md",
    "docs/setup-advisor.md",
    "tests/assess/test_setup_advisor.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 10
max_changed_lines = 230
allow_source_without_test_change = true
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: typescript-setup-advisor-script-fixtures

## Why this change intentionally large

Phase 171 adds fixture-backed setup-advisor TypeScript examples, docs, roadmap,
and DocSync trace in one small advisory evidence slice.

## Why this should not be split smaller

The tests and docs describe the same boundary: common script shapes should
trigger advice, but command bodies remain explicit user configuration.

## What allowed to change

Only setup-advisor tests, setup-advisor docs, Phase 170/171 roadmap docs,
DocSync trace or required attestations, and change-plan records may change.

## What must not change

Do not parse package script command bodies, infer package managers, add
TypeScript starter files, change setup-advisor runtime behavior, or make
TypeScript gates blocking.

## Verification plan

Run focused setup-advisor tests, DocSync check, roadmap docs tests,
markdownlint on touched docs, Tach, change-plan validation, and precommit
verifier before opening PR.

## Rollback plan

Revert branch remove fixture examples, docs wording, roadmap Phase 171, and
DocSync wording.

## Follow-up ratchet work

Later TypeScript/React slices can add setup-advisor examples for monorepo
package boundaries once command ownership semantics are designed.
