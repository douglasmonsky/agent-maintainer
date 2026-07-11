+++
id = "deep-audit-integration-series"
kind = "integration-branch-series"
status = "complete"
base_ref = "origin/main"
integration_branch = "codex/deep-release-evidence"
target_branch = "main"
merge_strategy = "merge-after-series"
expected_units = [
  "critical stabilization foundations", "configuration and background-verifier hardening", "exact-commit release evidence and workflow integrity",
  "version-matched public release contract", "dependency and public-governance remediation", "remaining roadmap reconciliation and final evidence",
]
expires = 2026-08-31
allowed_paths = [
  ".agent-maintainer/change-plans/**", ".docsync/**",
  ".github/**", ".gitignore",
  ".serena/**", "AGENTS.md",
  "CHANGELOG.md",
  "CODE_OF_CONDUCT.md",
  "CONTRIBUTING.md",
  "README.md",
  "SECURITY.md",
  "SUPPORT.md",
  "config/**",
  "docs/**",
  "justfile",
  "osv-scanner.toml",
  "package-lock.json",
  "package.json",
  "pyproject.toml",
  "src/**",
  "tach.toml",
  "tests/**",
  "zizmor.yml",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 385
max_changed_lines = 35000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Deep-Audit Integration Series

## Why this change intentionally large

The user-authorized deep audit became a focused commit series spanning the
critical-stabilization trust boundaries, configuration hardening, detached
verification, exact-commit release evidence, workflow integrity, public release
contract, dependency governance, and public-project governance. CI evaluates
the cumulative branch diff against `origin/main`, so the active plan must cover
that integration series rather than only its final release-contract tranche.

## Why this should not be split smaller

The work already lands in focused Conventional Commits with tranche-specific
historical plans. The final branch remains cohesive because its security,
configuration, generated-artifact, release-evidence, packaging, governance, and
roadmap claims must pass one exact-commit matrix before integration. Splitting
the cumulative CI comparison is not possible without losing that proof.
The scoped ceiling includes the audited Phase 176 notification-state, watcher
repair, heartbeat, event, privacy, and final-evidence work still listed below.

## What allowed to change

Change only the allowlisted repository paths needed by the recorded audit and
critical roadmap: implementation, focused tests, generated/currentness data,
workflows, public and historical documentation, realistic downstream fixtures,
dependency-risk records, governance files, and local semantic-tooling config.
Historical phase decisions may be linked or corrected for tracker drift but not
rewritten to claim evidence they did not have.

The user-authorized Serena setup detour may also add portable `.serena`
configuration and memories plus conditional repository guidance in `AGENTS.md`.
Machine-local JetBrains settings and backend selection must remain ignored.

## What must not change

Do not publish, tag, push, change external repository settings, touch production
configuration, invent completed evidence, weaken any quality or security gate,
or turn historical release notes into descriptions of unreleased behavior.

## Verification plan

Run focused checks for each tranche and retain its review evidence. Before final
integration, run the full, CI-equivalent, security, manual, and release profiles
on one clean exact commit; validate workflows and generated artifacts; test
built wheel and sdist entry points; validate local links and public docs; and
perform an independent diff, secrets, and private-data review.

## Follow-up ratchet work

After this branch lands, close this integration plan. Every future user-facing
merge must update Unreleased, and every release must add versioned notes plus
executable built-artifact evidence before the published-version pointer moves.

## Rollback plan

Revert focused commits or whole tranches in reverse order without rewriting
history. Never retain a version, security claim, release workflow, or public
contract that failed the same-commit matrix.
