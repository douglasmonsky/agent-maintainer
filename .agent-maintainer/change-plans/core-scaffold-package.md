+++
id = "core-scaffold-package"
kind = "refactor"
status = "active"
base_ref = "origin/main"
expires = 2026-07-14
allowed_paths = [
  "src/agent_maintainer/cli.py",
  "src/agent_maintainer/core/**",
  "tests/config/**",
  "tests/packaging/**",
  "docs/architecture/decisions/**",
  "docs/roadmap/phases/phase-04-config-scaffolding.md",
  "tach.toml",
  ".agent-maintainer/change-plans/**",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 20
max_changed_lines = 2500
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: core-scaffold-package

## Why this change intentionally large

`agent_maintainer.core` reached the structure-cohesion warning threshold with
initializer orchestration, starter-file templates, starter config text, and
policy presets living beside verifier runtime helpers. Moving that cluster into
`core.scaffold` addresses the warning while keeping the public `init` command
unchanged.

## Why this should not be split smaller

The four moved files import each other and represent one package-first
scaffolding responsibility. Splitting only one or two files would leave the
remaining flat modules with misleading ownership and would not remove the
cohesion pressure.

## What allowed to change

Move initializer/scaffolding modules into `src/agent_maintainer/core/scaffold`,
update imports, update Tach contracts, update tests that import the moved
modules, and document the architecture boundary.

## What must not change

Do not change public CLI names, initializer output semantics, starter config
contents, package metadata, verification profile semantics, or thresholds.

## Verification plan

Run focused initializer/config tests, `tach check --exact`, `change-plan check`,
`guidance --check`, and then the standard verifier profiles before merge.

## Rollback plan

Revert this PR. The old flat module paths are internal implementation details,
so rollback requires no user migration.

## Follow-up ratchet work

If `core.scaffold` grows beyond starter-file ownership, split by the new
responsibility instead of relaxing structure-cohesion thresholds.
