+++
id = "typescript-lcov-changed-line-facts"
kind = "feature"
status = "active"
base_ref = "b7b45b1"
expires = 2026-07-31
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  ".docsync/**",
  "docs/**",
  "src/agent_maintainer/test_intel/**",
  "src/agent_repair_facts/parsers/typescript_coverage.py",
  "tests/assess/test_typescript_lcov_external_fixtures.py",
  "tests/context/test_typescript_exact_facts.py",
  "tests/core/test_typescript_structured_output.py",
  "tests/docs/**",
  "tests/docsync/**",
  "tests/fixtures/typescript_lcov_external/**",
  "tests/repair_facts/test_typescript_lcov_records.py",
  "tests/test_intel/**",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 60
max_changed_lines = 5000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: typescript-lcov-changed-line-facts

## Why this change intentionally large

The TypeScript LCOV slice joins three existing contracts: reusable artifact
parsing, Git changed-line mapping, and advisory test-intelligence rendering. It
also records synthetic and pinned public compatibility evidence plus the public
documentation required to keep advisory and blocking semantics distinct.

## Why this should not be split smaller

The implementation is split into focused commits, but the parser, path-safe
workspace adapter, CLI, evidence, and docs form one user-visible report. Hosted
CI must validate their integrated JSON and text contract against one branch
base. The 5,000-line cap includes the approved design and executable plan; the
production and test slices remain independently reviewable.

## What allowed to change

Only TypeScript LCOV record parsing, the test-intelligence adapter/CLI and Tach
contract, direct synthetic and public replay tests, TypeScript/test-intelligence
docs, DocSync evidence, and these change-plan records may change.

## What must not change

Do not add a coverage command, package-manager inference, `diff-cover`
subprocess, threshold, ratchet, verifier profile, provider promotion, generated
file policy, or unrelated refactor. Do not weaken Python coverage enforcement
or the existing TypeScript artifact repair-fact contract.

## Verification plan

Implement parser, adapter, and CLI behavior test-first. Run focused parser,
test-intelligence, compatibility, docs, Tach, Archguard, Ruff, Pyright, and
DocSync checks, followed by a fresh full verifier, one comprehensive independent
review, and all hosted checks on a stacked draft pull request.

## Rollback plan

Revert the Phase 182 commits in reverse order. The feature creates no stored
baseline, migration, configured check, dependency, or external state, so
rollback requires no data repair.

## Follow-up ratchet work

Keep the report advisory. Package-manager audit facts and generated-file policy
are the next implementation slices. Any blocking threshold requires the later
promotion assessment and separate explicit design.
