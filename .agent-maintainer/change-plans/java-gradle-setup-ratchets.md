+++
id = "java-gradle-setup-ratchets"
kind = "feature"
status = "active"
base_ref = "origin/main"
expires = 2026-08-16
allowed_paths = [
  ".agent-maintainer/change-plans/java-gradle-foundation.md",
  ".agent-maintainer/change-plans/java-gradle-setup-ratchets.md",
  ".docsync/trace.yml",
  "config/agent-maintainer-capabilities.json",
  "docs/architecture/decisions/2026-07-16-java-gradle-setup-boundary.md",
  "docs/configuration-reference.md",
  "docs/provider-status.md",
  "docs/roadmap/overview.md",
  "docs/roadmap/polyglot-ecosystem-providers.md",
  "docs/setup-advisor.md",
  "pyproject.toml",
  "src/agent_maintainer/assess/evidence.py",
  "src/agent_maintainer/assess/models.py",
  "src/agent_maintainer/assess/setup_advisor.py",
  "src/agent_maintainer/assess/tach.domain.toml",
  "src/agent_maintainer/config/java.py",
  "src/agent_maintainer/core/setup_plans.py",
  "src/agent_maintainer/core/tach.domain.toml",
  "src/agent_maintainer/doctor/support/java_provider.py",
  "src/agent_maintainer/doctor/tach.domain.toml",
  "src/agent_maintainer/ecosystems/java/**",
  "src/agent_maintainer/ecosystems/tach.domain.toml",
  "src/agent_maintainer/skill/resources/agent-maintainer-setup/SKILL.md",
  "tests/archguard/test_decision_notes.py",
  "tests/assess/test_evidence.py",
  "tests/assess/test_setup_advisor*.py",
  "tests/config/test_config_reference.py",
  "tests/docs/test_first_touch_docs.py",
  "tests/docsync/test_public_doc_trace.py",
  "tests/doctor/test_java_doctor.py",
  "tests/ecosystems/java/**",
  "tests/ecosystems/test_java_runner.py",
  "tests/fixtures/java_gradle/**",
  "tests/skill/test_interaction_contract.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 46
max_changed_lines = 6000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: Java/Gradle Setup and Native Ratchets

## Why this change intentionally large

Pinned defaults, deterministic setup templates, typed semantic-edit handoffs,
task/report observations, native Spotless and SpotBugs ratchets, reviewed
post-edit validation, and CI planning form one safe setup workflow. Partial
delivery would advertise setup choices without a complete validation boundary.

## Why this should not be split smaller

Implementation uses one focused commit per written task, but the repository
budget evaluates the whole branch against `origin/main`. This phase plan covers
only setup and native-ratchet work while excluding structured debt baselines and
coverage rollout.

## What allowed to change

Only the setup, defaults, templates, observations, bounded SpotBugs XML, doctor,
advisor, skill, documentation, architecture, fixtures, and focused tests listed
above.

## What must not change

Do not regex-rewrite arbitrary builds, download during normal tests, mutate a
baseline during verification, add Checkstyle/PMD debt baselines, enforce JaCoCo
thresholds, use system Gradle, or weaken the checked-wrapper boundary.

## Verification plan

Use RED/GREEN focused tests for each task. At the phase gate run all setup and
native-ratchet tests, Tach, DocSync, doctor, and one fresh `just v`.

## Rollback plan

Revert the focused setup/native-ratchet commits in reverse order. Generated
plans are preview-first and no production or external state is changed.

## Follow-up ratchet work

Complete this plan before activating structured Checkstyle/PMD baselines or
JaCoCo coverage rollout.
