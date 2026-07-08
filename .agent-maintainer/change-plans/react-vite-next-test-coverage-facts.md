+++
id = "react-vite-next-test-coverage-facts"
kind = "feat"
status = "complete"
base_ref = "origin/main"
expires = 2026-07-22
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  "src/agent_repair_facts/parsers/typescript_diagnostics.py",
  "src/agent_repair_facts/parsers/typescript_coverage.py",
  "src/agent_repair_facts/parsers/typescript_tests.py",
  "src/agent_repair_facts/parsers/typescript.py",
  "src/agent_repair_facts/registry.py",
  "src/agent_repair_facts/tach.domain.toml",
  "src/agent_maintainer/core/tach.domain.toml",
  "src/agent_maintainer/ecosystems/tach.domain.toml",
  "src/agent_maintainer/core/structured_typescript.py",
  "src/agent_maintainer/context/pack/typescript_fact_parsers.py",
  "src/agent_maintainer/ecosystems/typescript/diagnostics.py",
  "tests/core/test_typescript_structured_output.py",
  "tests/context/test_typescript_exact_facts.py",
  "tests/docs/test_first_touch_docs.py",
  "docs/typescript-javascript-provider.md",
  "docs/case-studies/typescript-provider-maturation.md",
  "docs/ROADMAP.md",
  "docs/architecture/decisions/2026-07-08-typescript-coverage-parser-boundary.md",
  "docs/roadmap/full-roadmap-blueprint.md",
  "docs/roadmap/phases/phase-167-react-vite-next-structured-test-and-coverage-facts.md",
  ".docsync/trace.yml",
  ".docsync/attestations/**",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 28
max_changed_lines = 930
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: react-vite-next-test-coverage-facts

## Why this change intentionally large

This branch implements Phase 167 by extending TypeScript test repair facts,
coverage artifact facts, docs, roadmap status, and DocSync trace in one
reviewable slice.

## Why this should not be split smaller

Parser support without tests or public docs would overstate maturity, while docs
without parser evidence would drift from implementation. The changed files form
one bounded TypeScript repair-fact capability.

## What allowed to change

Only TypeScript test/coverage parser support, compatibility shims, focused
tests, roadmap/docs references, DocSync trace wording, and change-plan records
may change.

## What must not change

Do not execute Node tools, infer package managers or frameworks, add TypeScript
coverage enforcement, relax verifier thresholds, or promote TypeScript/React to
blocking status.

## Verification plan

Run focused TypeScript structured-output and exact-fact tests, docs/DocSync
tests, DocSync check, Ruff on touched Python files, `git diff --check`, Tach,
change-plan validation, and one broad verifier profile before merging.

## Rollback plan

Revert this branch to remove Vitest task JSON and TypeScript coverage artifact
repair facts plus the corresponding docs and roadmap updates.

## Follow-up ratchet work

Use the new parser evidence during Phase 168 doctor/setup work to recommend
stable JSON and coverage artifact commands without inferring package managers.
