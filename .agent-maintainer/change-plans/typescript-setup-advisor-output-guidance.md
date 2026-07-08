+++
id = "typescript-setup-advisor-output-guidance"
kind = "feat"
status = "active"
base_ref = "origin/main"
expires = 2026-07-22
allowed_paths = [
    ".agent-maintainer/change-plans/**",
    ".docsync/attestations/**",
    ".docsync/trace.yml",
  "docs/roadmap/full-roadmap-blueprint.md",
  "docs/roadmap/phases/phase-169-typescript-repair-fact-output-guidance.md",
  "docs/roadmap/phases/phase-170-typescript-setup-advisor-output-guidance.md",
  "docs/setup-advisor.md",
  "src/agent_maintainer/assess/setup_advisor.py",
  "tests/assess/test_setup_advisor.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 10
max_changed_lines = 180
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: typescript-setup-advisor-output-guidance

## Why this change intentionally large

This Phase 170 slice moves the TypeScript repair-fact output recommendation into
the setup-advisor adoption flow, with docs and focused tests that keep the
guidance advisory.

## Why this should not be split smaller

The setup-advisor recommendation, public docs, roadmap row, and tests describe
one user-visible adoption hint. Splitting them would either under-document the
behavior or test wording that is not exposed.

## What allowed to change

Only setup-advisor TypeScript recommendation wording, focused setup-advisor
tests, setup-advisor docs, Phase 169/170 roadmap docs, DocSync trace, and
change-plan records may change.

## What must not change

Do not infer package managers, inspect script command bodies, add new config
fields, add starter files, add TypeScript coverage adapters, or make TypeScript
reviewability blocking.

## Verification plan

Run focused setup-advisor tests, DocSync check, markdownlint on touched docs,
Ruff on touched Python files, Tach, change-plan validation, and a precommit
verifier before opening the PR.

## Rollback plan

Revert this branch to restore the previous setup-advisor TypeScript
recommendation wording.

## Follow-up ratchet work

Later TypeScript/React slices can add fixture-backed setup-advisor examples for
pnpm, Vite, and Next.js repositories without changing this advisory boundary.
