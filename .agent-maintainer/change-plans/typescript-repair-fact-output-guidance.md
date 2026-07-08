+++
id = "typescript-repair-fact-output-guidance"
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
  "docs/roadmap/phases/phase-169-typescript-repair-fact-output-guidance.md",
  "docs/typescript-javascript-provider.md",
  "src/agent_maintainer/doctor/support/providers.py",
  "tests/docs/test_first_touch_docs.py",
  "tests/doctor/test_typescript_doctor.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 12
max_changed_lines = 280
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: typescript-repair-fact-output-guidance

## Why this change intentionally large

This Phase 169 slice adds TypeScript repair-fact output advice to the doctor and
updates the public provider docs, roadmap, DocSync trace, and focused tests that
keep the advisory behavior bounded.

## Why this should not be split smaller

The doctor row and provider docs describe the same setup behavior. Splitting the
tests or docs away from the implementation would make the experimental provider
surface harder to review and easier to overstate.

## What allowed to change

Only TypeScript provider doctor guidance, focused doctor/docs tests, provider
status docs, Phase 168/169 roadmap docs, DocSync trace/attestations, and
change-plan records may change.

## What must not change

Do not add package-manager autodetection, new TypeScript config fields,
generated starter files, coverage command adapters, dependency/security/mutation
adapters, or blocking TypeScript reviewability gates.

## Verification plan

Run focused TypeScript doctor and docs tests, DocSync check, markdownlint on
touched docs, Ruff on touched Python files, Tach, change-plan validation, and a
precommit verifier before opening the PR.

## Rollback plan

Revert this branch to remove the advisory doctor row and restore previous
TypeScript provider docs.

## Follow-up ratchet work

Later TypeScript/React slices can promote fixture-backed setup guidance into a
dedicated setup-advisor surface if the generic doctor row becomes too cramped.
