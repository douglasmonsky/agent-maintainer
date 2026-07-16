+++
id = "java-gradle-coverage-rollout"
kind = "feature"
status = "active"
base_ref = "fc65b29bc2ae8d9187a29cc1fb365f1eeac0d030"
expires = 2026-07-30
allowed_paths = [
  ".agent-maintainer/change-plans/java-gradle-coverage-rollout.md",
  ".docsync/trace.yml",
  ".github/workflows/deep-verify.yml",
  ".github/workflows/java-gradle-live.yml",
  ".github/workflows/verify.yml",
  "README.md",
  "justfile",
  "pyproject.toml",
  "config/agent-maintainer-capabilities.json",
  "docs/architecture/decisions/**",
  "docs/case-studies/java-gradle-provider-calibration.md",
  "docs/configuration-reference.md",
  "docs/java-gradle-provider.md",
  "docs/provider-contribution-guide.md",
  "docs/provider-status.md",
  "docs/roadmap/**",
  "docs/setup-advisor.md",
  "docs/superpowers/plans/2026-07-16-java-gradle-coverage-rollout.md",
  "docs/supported-scans-and-agent-use.md",
  "src/agent_maintainer/config/**",
  "src/agent_maintainer/doctor/support/java_provider.py",
  "src/agent_maintainer/ecosystems/java/**",
  "src/agent_maintainer/ecosystems/tach.domain.toml",
  "src/agent_maintainer/skill/resources/agent-maintainer-setup/**",
  "tests/assess/test_java_real_repo_calibration.py",
  "tests/config/**",
  "tests/docs/**",
  "tests/docsync/**",
  "tests/ecosystems/java/**",
  "tests/ecosystems/test_java_runner.py",
  "tests/fixtures/java_gradle/**",
  "tests/live/java_gradle/**",
  "tests/packaging/test_parallel_verify_workflow.py",
  "tests/packaging/test_github_actions_policy.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 90
max_changed_lines = 9000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: java-gradle-coverage-rollout

## Why this change intentionally large
Exact JaCoCo policy, truthful project topology, live cached Gradle validation,
calibration evidence, and public maturity documentation are one promotion gate.
Shipping only a percentage parser would advertise enforcement without proving
how reports map to real single- and multi-project builds.

## Why this should not be split smaller
The runner contract and public provider status depend on the same topology and
threshold semantics exercised by the live fixtures. Splitting those surfaces
would leave an unverifiable intermediate state or duplicate fixture policy.

## What allowed to change
Only Java configuration, report policy, setup/runner integration, bounded live
fixtures, experimental workflows, calibration evidence, and their directly
traced documentation/tests may change.

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
