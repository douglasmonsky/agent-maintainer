+++
id = "docsync-standalone-readiness"
kind = "migration"
status = "complete"
base_ref = "origin/main"
expires = 2026-07-21
allowed_paths = ["src/docsync/**", "tests/docsync/**", "tests/docs/**", "docs/docsync*.md", "examples/docsync/**", ".docsync/trace.yml", ".agent-maintainer/change-plans/**", "pyproject.toml", "docs/architecture/decisions/**", "src/archguard/decision_notes.py", "tests/archguard/test_decision_notes.py"]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 40
max_changed_lines = 4000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: docsync-standalone-readiness

## Why this change intentionally large

DocSync is moving from an internal dogfood utility toward a standalone product
surface. That requires keeping source, tests, docs, trace metadata, and examples
aligned so extraction remains mechanical instead of becoming a later redesign.

## Why this should not be split smaller

The work should still land in small commits, but the active branch needs one
scope that permits DocSync docs, trace metadata, focused tests, and examples to
change together. Splitting the policy scope would cause valid DocSync trace
updates to fail while the product contract is being documented.

## What allowed to change

Allowed changes are limited to DocSync package code, DocSync tests, DocSync docs,
DocSync examples, DocSync trace metadata, package metadata required for the
DocSync command surface, this change-plan directory, and architecture
decision-note updates strictly required by DocSync Tach domain contract changes.

## What must not change

Do not change production credentials, external account settings, unrelated
Agent Maintainer checks, non-DocSync architecture boundaries, deployment
configuration, or broad repository structure.

## Verification plan

Run DocSync doctor, DocSync check, the focused `tests/docsync` suite, and
`git diff --check`. Run broader verification only when DocSync package code,
packaging, or integration behavior changes.

## Rollback plan

Revert DocSync readiness commits and restore the previous change-plan scope if
wait-orchestration work resumes on this branch. Since generated `.docsync/out/`
files are not source truth, no generated artifacts need manual rollback.

## Follow-up ratchet work

Ratchet toward a standalone README, minimal fixture repository, command authoring
helpers, and eventual package extraction once the schema and CLI contract are
stable.
