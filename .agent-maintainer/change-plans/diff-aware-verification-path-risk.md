+++
id = "diff-aware-verification-path-risk"
kind = "feature"
status = "complete"
base_ref = "a119b0d"
expires = 2026-08-01
allowed_paths = [
  ".agent-maintainer/change-plans/diff-aware-verification-path-risk.md",
  ".agent-maintainer/path-risk.toml",
  ".docsync/**",
  "README.md",
  "docs/ROADMAP.md",
  "docs/architecture/decisions/2026-07-18-diff-aware-verification-planning.md",
  "docs/architecture/subsystem-stability.md",
  "docs/roadmap/full-roadmap-blueprint.md",
  "docs/roadmap/phases/phase-183-diff-aware-verification-planning.md",
  "docs/superpowers/plans/2026-07-18-diff-aware-verification-path-risk.md",
  "docs/superpowers/specs/2026-07-18-diff-aware-verification-path-risk-design.md",
  "docs/tool-map.md",
  "src/agent_maintainer/catalogs/catalog.py",
  "src/agent_maintainer/catalogs/global_checks.py",
  "src/agent_maintainer/catalogs/tach.domain.toml",
  "src/agent_maintainer/cli.py",
  "src/agent_maintainer/config/preflight.py",
  "src/agent_maintainer/core/executor.py",
  "src/agent_maintainer/core/repo_paths.py",
  "src/agent_maintainer/core/tach.domain.toml",
  "src/agent_maintainer/ecosystems/git_changes.py",
  "src/agent_maintainer/ecosystems/tach.domain.toml",
  "src/agent_maintainer/verification_plan/**",
  "src/agent_maintainer/verify/groups.py",
  "tach.toml",
  "tests/catalogs/test_config_catalog.py",
  "tests/catalogs/test_python_catalog_characterization.py",
  "tests/config/test_config_cli_boundary.py",
  "tests/core/test_repo_paths.py",
  "tests/ecosystems/test_git_changes.py",
  "tests/packaging/test_public_docs.py",
  "tests/packaging/test_script_helpers.py",
  "tests/regression/test_phase10_error_paths.py",
  "tests/runtime_events/test_command_runtime_events.py",
  "tests/verification_plan/**",
  "tests/verify/test_verification_groups.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 75
max_changed_lines = 5500
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: diff-aware-verification-path-risk

## Why this change intentionally large

The feature joins neutral Git change identity, provider-aware unit resolution,
strict repository policy, deterministic planning, CLI output, verifier catalog
integration, architecture contracts, and public documentation. These surfaces
form one control-layer contract: a changed path must map to the same named
evidence in local planning, automated enforcement, and hosted review.
The file count includes DocSync-generated attestations for existing public
claims invalidated by the new command registry and catalog entry; those records
are individually generated, scoped evidence rather than implementation breadth.

## Why this should not be split smaller

The implementation is divided into focused commits, but publishing the planner
without its policy validator would be advisory-only scaffolding, while
publishing the enforcement check without stable planning output would be opaque.
The rename/delete semantics, affected-unit mapping, and repository policy must
be validated against one branch base so no sensitive path can bypass evidence.

## What allowed to change

Only the new verification-planning domain, neutral repository-path and Git
change boundaries, direct catalog/CLI/Tach integration, synthetic tests, the
initial path-risk policy and ADR, roadmap/public documentation, DocSync evidence,
and these approved design and plan records may change.

## What must not change

Do not remove or dynamically suppress existing verifier checks, execute checks
inside the planner, add a runtime dependency, infer compatibility version bumps,
classify failures, promote ecosystem providers, add remote review mutations, or
perform unrelated refactors.

## Verification plan

Implement every behavior test-first. Run focused path, Git, policy, unit,
planner, CLI, catalog, docs, and runtime-event suites; exact Tach and Archguard
checks; DocSync; the public command against synthetic diffs; a fresh full
verifier; one comprehensive independent review; and all hosted protected checks.

## Rollback plan

Revert the Phase 183 commits in reverse order. The feature writes no baseline,
migration, production data, credential, or external account state. Removing the
optional catalog entry and policy file restores the previous fixed-profile
behavior without data repair.

## Follow-up ratchet work

Keep check execution additive in Phase 183. Contract/version ratchets, failure
fingerprinting, Playwright/Electron/accessibility facts, and flake/performance
budgets remain separate roadmap phases after the planner schema proves stable.
