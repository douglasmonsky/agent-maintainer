+++
id = "java-gradle-foundation"
kind = "feature"
status = "active"
base_ref = "origin/main"
expires = 2026-08-16
allowed_paths = [
  ".agent-maintainer/change-plans/beta7-release.md",
  ".agent-maintainer/change-plans/java-gradle-support-design.md",
  ".agent-maintainer/change-plans/java-gradle-foundation.md",
  ".docsync/trace.yml",
  "docs/architecture/decisions/2026-07-16-java-gradle-provider-boundary.md",
  "docs/configuration-reference.md",
  "docs/provider-status.md",
  "docs/roadmap/overview.md",
  "docs/roadmap/polyglot-ecosystem-providers.md",
  "docs/superpowers/plans/2026-07-16-java-gradle-*.md",
  "docs/superpowers/specs/2026-07-15-java-gradle-support-*.md",
  "src/agent_maintainer/assess/evidence.py",
  "src/agent_maintainer/assess/models.py",
  "src/agent_maintainer/config/*.py",
  "src/agent_maintainer/doctor/cli.py",
  "src/agent_maintainer/doctor/support/policy.py",
  "src/agent_maintainer/doctor/support/providers.py",
  "src/agent_maintainer/ecosystems/java/**",
  "src/agent_maintainer/ecosystems/registry.py",
  "src/agent_maintainer/ecosystems/tach.domain.toml",
  "src/agent_maintainer/verify/groups.py",
  "tests/archguard/test_decision_notes.py",
  "tests/assess/test_evidence.py",
  "tests/catalogs/test_global_catalog_characterization.py",
  "tests/catalogs/test_java_catalog.py",
  "tests/catalogs/test_provider_registry.py",
  "tests/catalogs/test_typescript_catalog.py",
  "tests/config/test_*.py",
  "tests/docsync/test_public_doc_trace.py",
  "tests/doctor/test_doctor.py",
  "tests/doctor/test_java_doctor.py",
  "tests/doctor/test_typescript_doctor.py",
  "tests/ecosystems/test_file_changes.py",
  "tests/ecosystems/test_java_*.py",
  "tests/ecosystems/test_python_classification.py",
  "tests/ecosystems/test_typescript_*.py",
  "tests/fixtures/java_gradle/**",
  "tests/verify/test_verification_groups.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 60
max_changed_lines = 6000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: Java/Gradle Provider Foundation

## Why this change intentionally large

The nested configuration, provider registry, repository classification,
checked-wrapper boundary, command-only runner, doctor, and verification groups
form one usable experimental provider foundation. Shipping only a subset would
either expose configuration that cannot run or execution that cannot be
diagnosed safely.

## Why this should not be split smaller

Implementation still proceeds in focused commits, but the repository change
budget evaluates the complete branch against `origin/main`. One active plan
therefore covers the already-approved design and the six coupled foundation
tasks while exact paths and phase gates prevent later report/baseline scope.

## What allowed to change

Only the approved Java design/plans and the Phase 1 configuration, evidence,
classification, provider, wrapper, runner, doctor, architecture, documentation,
fixtures, and focused tests listed above.

## What must not change

Do not implement report parsing, setup templates, debt baselines, JaCoCo
thresholds, live Gradle workflows, system-Gradle fallback, compatibility aliases,
or public parity claims. Preserve Python and TypeScript behavior.

## Verification plan

Use RED/GREEN focused tests for each task. At the phase gate run the two focused
test blocks from the foundation plan, `just doctor`, and `just v`. Run Tach and
the architecture-decision test for the Java domain boundary.

## Rollback plan

Revert the focused foundation commits in reverse order. The provider is disabled
by default and has no external or data migration state.

## Follow-up ratchet work

Complete this plan before activating the setup/native-ratchet plan. Do not move
report parsing, baselines, coverage, or live Gradle work into this budget.
