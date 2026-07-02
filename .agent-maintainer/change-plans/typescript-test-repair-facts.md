+++
id = "typescript-test-repair-facts"
kind = "focused-fix"
status = "active"
base_ref = "origin/main"
expires = 2026-07-16
allowed_paths = [
  ".agent-maintainer/change-plans/typescript-test-repair-facts.md",
  "docs/ROADMAP.md",
  "docs/roadmap/full-roadmap-blueprint.md",
  "docs/roadmap/phases/phase-104-typescript-test-repair-facts.md",
  "docs/typescript-javascript-provider.md",
  "src/agent_maintainer/context/pack/fact_parsers.py",
  "src/agent_maintainer/context/pack/typescript_fact_parsers.py",
  "src/agent_maintainer/core/reporting.py",
  "src/agent_maintainer/core/structured_typescript.py",
  "src/agent_maintainer/ecosystems/typescript/diagnostics.py",
  "tests/context/test_typescript_exact_facts.py",
  "tests/core/test_typescript_structured_output.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 12
max_changed_lines = 500
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: typescript-test-repair-facts

## Why this change intentionally large
TypeScript test repair facts touch the parser, compact summary dispatch, exact
fact dispatch, tests, and user-facing provider docs together. Splitting those
files across unrelated branches would leave either undocumented behavior or
unwired parser code.

## Why this should not be split smaller
The implementation is still one behavior: parse configured `typescript-test`
JSON output into concise repair facts. The test-intelligence matcher does not
currently map `src/agent_maintainer/ecosystems/typescript/diagnostics.py` to
the core structured-output tests, so this plan records the intentional source
and test relationship instead of weakening the gate.

## What allowed to change
Only the TypeScript diagnostics parser, TypeScript summary/fact dispatch, the
focused TypeScript summary and exact-fact tests, the TypeScript provider docs,
and roadmap tracking for Phase 104.

## What must not change
No package-manager autodetection, no TypeScript blocking gates, no TypeScript
coverage/mutation support, no Go provider restoration, no Python provider
behavior change, and no config semantics change.

## Verification plan
Run focused TypeScript parser, summary, and exact-fact tests; run Ruff,
Pyright, and wemake on touched package files; run `guidance --check`,
`change-plan check`, `tach check --exact`, `verify --profile precommit`,
`full`, `ci`, `security`, and `manual`.

## Rollback plan
Revert the TypeScript parser and dispatch changes together with their tests and
docs. Existing TypeScript lint/typecheck structured summaries should continue
to work because this branch does not change their parser contracts.

## Follow-up ratchet work
Consider teaching test intelligence that TypeScript ecosystem parser changes
are covered by `tests/core/test_typescript_structured_output.py` and
`tests/context/test_typescript_exact_facts.py`.
