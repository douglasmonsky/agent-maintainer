+++
id = "typescript-react-doctor-setup-guidance"
kind = "feat"
status = "active"
base_ref = "origin/main"
expires = 2026-07-22
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  ".docsync/attestations/**",
  ".docsync/trace.yml",
  "docs/provider-status.md",
  "docs/roadmap/full-roadmap-blueprint.md",
  "docs/roadmap/phases/phase-168-typescript-react-doctor-and-setup-guidance.md",
  "docs/typescript-javascript-provider.md",
  "src/agent_maintainer/doctor/support/providers.py",
  "tests/docs/test_first_touch_docs.py",
  "tests/doctor/test_typescript_doctor.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 12
max_changed_lines = 180
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: typescript-react-doctor-setup-guidance

## Why this change intentionally large

This Phase 168 slice updates TypeScript doctor setup hints together with the
public provider docs, DocSync trace, and focused tests that make the new
guidance reviewable.

## Why this should not be split smaller

Changing doctor output without docs would leave public setup guidance stale.
Changing docs without the doctor tests would overstate behavior. The files form
one bounded user-facing setup guidance change.

## What allowed to change

Only TypeScript provider doctor hint wording, focused doctor/docs tests,
provider status docs, Phase 168 roadmap docs, DocSync trace/attestations, and
change-plan records may change.

## What must not change

Do not add package-manager autodetection, generated TypeScript starter files,
coverage command adapters, dependency/security/mutation adapters, or blocking
TypeScript reviewability gates.

## Verification plan

Run focused TypeScript doctor and docs tests, DocSync check, markdownlint on
touched docs, Ruff on touched Python files, Tach, change-plan validation, and a
precommit verifier before opening the PR.

## Rollback plan

Revert this branch to restore previous TypeScript doctor hints and public docs.

## Follow-up ratchet work

Later Phase 168 work can add setup-advisor recommendations for stable
TypeScript test and coverage artifact scripts once more fixture evidence exists.
