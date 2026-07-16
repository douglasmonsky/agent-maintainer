+++
id = "java-gradle-structured-baselines"
kind = "feature"
status = "active"
base_ref = "origin/main"
expires = 2026-08-16
allowed_paths = [
  ".agent-maintainer/change-plans/java-gradle-setup-ratchets.md",
  ".agent-maintainer/change-plans/java-gradle-structured-baselines.md",
  ".docsync/trace.yml",
  "docs/architecture/decisions/2026-07-16-java-gradle-setup-boundary.md",
  "docs/architecture/decisions/2026-07-16-java-gradle-structured-evidence-boundary.md",
  "docs/configuration-reference.md",
  "docs/provider-contribution-guide.md",
  "docs/provider-status.md",
  "docs/ratcheting.md",
  "docs/setup-advisor.md",
  "docs/superpowers/plans/2026-07-16-java-gradle-structured-baselines.md",
  "docs/supported-scans-and-agent-use.md",
  "src/agent_maintainer/assess/cli.py",
  "src/agent_maintainer/assess/file_baselines.py",
  "src/agent_maintainer/assess/tach.domain.toml",
  "src/agent_maintainer/config/coercion.py",
  "src/agent_maintainer/config/reference.py",
  "src/agent_maintainer/config/registry.py",
  "src/agent_maintainer/config/schema.py",
  "src/agent_maintainer/config/schema_fields.py",
  "src/agent_maintainer/config/source_validation.py",
  "src/agent_maintainer/config/tach.domain.toml",
  "src/agent_maintainer/config/validation.py",
  "src/agent_maintainer/core/structured_artifacts.py",
  "src/agent_maintainer/core/tach.domain.toml",
  "src/agent_maintainer/doctor/support/java_provider.py",
  "src/agent_maintainer/doctor/tach.domain.toml",
  "src/agent_maintainer/ecosystems/java/**",
  "src/agent_maintainer/ecosystems/tach.domain.toml",
  "src/agent_maintainer/skill/resources/agent-maintainer-setup/SKILL.md",
  "src/agent_repair_facts/parsers/java.py",
  "src/agent_repair_facts/registry.py",
  "src/agent_repair_facts/tach.domain.toml",
  "tests/assess/test_file_baselines.py",
  "tests/assess/test_java_baseline_cli.py",
  "tests/config/**",
  "tests/context/test_java_exact_facts.py",
  "tests/core/test_structured_artifact_summaries.py",
  "tests/docs/test_first_touch_docs.py",
  "tests/docsync/test_public_doc_trace.py",
  "tests/doctor/test_java_doctor.py",
  "tests/ecosystems/java/**",
  "tests/ecosystems/test_java_runner.py",
  "tests/fixtures/java_gradle/**",
  "tests/packaging/test_package_metadata.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 62
max_changed_lines = 7000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: Java/Gradle Structured Baselines

## Why this change intentionally large

Bounded report adapters, stable finding identities, multiset debt comparison,
repair facts, explicit baseline lifecycle commands, and provider-neutral file
ceilings form one evidence contract. Shipping only a parser or writer would
create an unsupported partial enforcement surface.

## Why this should not be split smaller

Focused commits remain mandatory for each written task. The phase-level budget
must cover the shared finding schema from fresh Gradle evidence through repair
output and explicit lifecycle operations without mixing in coverage rollout.

## What allowed to change

Only the Java report/finding/baseline pipeline, provider-neutral file ceilings,
their CLI and repair-fact integrations, architecture/config documentation, and
focused tests listed above.

## What must not change

Do not mutate baselines during verification, weaken Gradle exit authority,
persist raw third-party XML in Agent Maintainer artifacts, add JaCoCo threshold
ratchets, introduce aliases or compatibility shims, or make Java policy leak
into the provider-neutral file comparator.

## Verification plan

Use RED/GREEN tests per task. At the gate run all Java ecosystem, file-baseline,
config, exact-fact, DocSync, doctor, and full verification checks.

## Rollback plan

Revert the focused structured-evidence commits in reverse order. Baseline writes
remain explicit and reviewable; no production or external state is changed.

## Follow-up ratchet work

Complete this plan before activating JaCoCo threshold ratchets, live Gradle CI,
or calibration/public-rollout work.
