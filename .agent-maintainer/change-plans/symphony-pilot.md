+++
id = "symphony-pilot"
kind = "mechanical-migration"
status = "active"
base_ref = "origin/main"
expires = 2026-08-07
allowed_paths = [
  ".agent-maintainer/change-plans/symphony-pilot.md",
  ".agent-maintainer/change-plans/typescript-package-manager-audit-release.md",
  ".agents/skills/symphony-github-work/**",
  ".github/ISSUE_TEMPLATE/autonomous_task.yml",
  "AGENTS.md",
  "WORKFLOW.md",
  "config/dev-lock.txt",
  "docs/symphony/**",
  "scripts/run-symphony",
  "scripts/symphony-git",
  "scripts/start-symphony",
  "scripts/status-symphony",
  "scripts/stop-symphony",
  "scripts/verify",
]
forbidden_paths = [
  ".env",
  ".env.*",
  ".github/workflows/**",
  "config/prod/**",
  "pyproject.toml",
  "src/**",
  "tests/**",
]
max_changed_files = 20
max_changed_lines = 2500
allow_source_without_test_change = true
requires_tests = false
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: symphony-pilot

## Why this change intentionally large

The pilot is one operational contract spanning issue intake, Symphony runtime
configuration, a restricted Codex profile, worker delivery guidance, service
controls, observability, security documentation, and validation evidence.
Leaving any of those surfaces out would produce an un-runnable or unsafe pilot.

## Why this should not be split smaller

Before merge, the live Symphony run must clone this branch and prove that the
workflow, skill, scripts, issue labels, verification, and documentation agree.
Splitting them would make the first autonomous worker depend on unmerged or
undocumented behavior and would prevent an end-to-end review of the safety
boundary.

## What allowed to change

Only the root Symphony contract, the autonomous issue form, the
`symphony-github-work` skill, service and verification scripts, the four
Symphony documents, root agent guidance, this plan, the stale status field in
the completed TypeScript publication plan, and a security-only refresh to the
development lock may change. The lock refresh is allowed only because the
required full gate identified newly published advisories with upstream fixes.

## What must not change

Application source, tests, production configuration, GitHub Actions, dependency
inputs, architecture contracts, release behavior, credentials, branch
protection, and existing issue templates must not change.

## Verification plan

Validate skill metadata, Bash syntax, ShellCheck, YAML, Markdown, Git diff
whitespace, Agent Maintainer change-plan/doctor checks, and the full
`scripts/verify` gate. Then run a live GitHub issue-to-workspace-to-PR scenario,
a safe blocked-state scenario, the stock dashboard/API, the structured status
command, start/stop behavior, and Desktop workspace opening.

## Rollback plan

Remove the four lifecycle labels, stop the per-user service, point the stable
Symphony link back to the prior version or remove it, close the pilot PR without
merging, and leave all issue workspaces intact for manual inspection. No
production data or repository security setting changes are required to roll
back.

## Follow-up ratchet work

After the pilot, replace the current broad GitHub credential with a dedicated
repository-only identity, evaluate Serena and GitNexus in disposable isolated
workspaces, and consider concurrency two only after repeated successful runs.
