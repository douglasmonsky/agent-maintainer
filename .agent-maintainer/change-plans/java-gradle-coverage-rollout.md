+++
id = "java-gradle-coverage-rollout"
kind = "feature"
status = "complete"
base_ref = "3511d61c118ac3604b8f9f8cc7cba9dc5fa2df7b"
expires = 2026-07-30
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  ".docsync/**",
  ".github/workflows/**",
  ".gitignore",
  "CHANGELOG.md",
  "README.md",
  "config/agent-maintainer-capabilities.json",
  "config/dependency-risks.toml",
  "config/dev-lock.txt",
  "docs/**",
  "justfile",
  "osv-scanner.toml",
  "pyproject.toml",
  "src/agent_maintainer/assess/**",
  "src/agent_maintainer/checks/change_budget.py",
  "src/agent_maintainer/config/**",
  "src/agent_maintainer/core/**",
  "src/agent_maintainer/doctor/**",
  "src/agent_maintainer/ecosystems/**",
  "src/agent_maintainer/skill/resources/agent-maintainer-setup/**",
  "src/agent_maintainer/runners/pyright_strict_baseline.py",
  "src/agent_maintainer/verify/**",
  "src/agent_repair_facts/**",
  "tests/**",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 250
max_changed_lines = 18100
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: java-gradle-coverage-rollout

## Why this change intentionally large

The final CI gate evaluates the complete phased Java/Gradle rollout from its
branch base: provider foundation, reviewed setup, native and external ratchets,
structured evidence, exact JaCoCo policy, live cached Gradle validation,
calibration evidence, and public maturity documentation. Earlier phase plans
kept each implementation slice reviewable; this closeout plan records their
combined branch envelope without changing repository-wide thresholds.
The narrow file-count and documentation scope also cover the versioned release
record that must travel through the same protected-branch PR; no unrelated
exception is introduced.
The final hosted Windows proof adds one workflow correction and its contract
test, so the plan reserves a seven-file and 86-line margin above the resulting
243-file, 18,014-line closeout diff.
The final verification pass also surfaced newly published MCP advisories in
Semgrep's exact transitive pin. The same closeout records the narrow, expiring
dependency-risk exception required until Semgrep permits the fixed MCP release.

## Why this should not be split smaller

The branch is already split into focused phase commits and completed subordinate
plans. CI must nevertheless validate the integrated branch as one diff because
the runner, setup templates, report policy, and public provider status depend on
the same contracts.

## What allowed to change

Only the completed Java provider phases, the provider-neutral seams they
deliberately extend, bounded fixtures/workflows, directly traced
documentation/tests, and the corresponding beta release record may change.

## What must not change

Do not add system-Gradle fallbacks, synthetic aggregate percentages, verifier
baseline mutation, compatibility aliases, unsafe XML parsing, parity claims,
or changes to unrelated providers and release behavior.

## Verification plan

Implement each plan task test-first. Run focused Java/config/workflow/docs tests,
exact Tach and canonical Pyright, DocSync, live checked-wrapper fixtures, doctor,
commit verification, and the full verifier before promotion closeout.

## Rollback plan

Revert the phase commits in reverse order. Threshold policy remains separate
from Java findings/file baselines, so rollback does not require data migration.

## Follow-up ratchet work

Keep the provider experimental until every promotion gate passes. Any live
repository-specific tuning must be explicit and must never lower stored floors
silently.
