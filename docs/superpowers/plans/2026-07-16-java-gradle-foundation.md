# Java/Gradle Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a disabled-by-default experimental Java/Gradle provider with frozen nested configuration, static repository evidence, conservative classification, checked-wrapper confinement, grouped checks, and a hermetic runner.

**Architecture:** Keep the existing command-only `Check` seam. The provider plans three checks; an internal Python runner owns Gradle invocation and emits one bounded JSON artifact. Configuration owns public contracts; the Java package owns Gradle behavior. No report parsing or ratchets enter this phase.

**Tech Stack:** Python 3.11+, frozen dataclasses, pytest, TOML, Gradle wrapper shell fixtures, Tach.

## Global Constraints

- Follow the approved Java design, contracts, and validation specification.
- Use only a checked-in wrapper confined beneath `gradle_root`; never PATH Gradle.
- Preserve Python and TypeScript behavior and provider ordering.
- Use test-first RED/GREEN cycles and one focused commit per task.
- Do not add compatibility aliases, Gradle Tooling API, init scripts, or custom plugins.

---

### Task 1: Characterize shared seams and activate the phase budget

**Files:**

- Modify: `.agent-maintainer/change-plans/java-gradle-support-design.md`
- Create: `.agent-maintainer/change-plans/java-gradle-foundation.md`
- Test: `tests/catalogs/test_global_catalog_characterization.py`
- Test: `tests/catalogs/test_provider_registry.py`
- Test: `tests/config/test_config_loading.py`
- Test: `tests/verify/test_verification_groups.py`

- [x] Add assertions fixing current Python/TypeScript catalog order, direct `enable_typescript` behavior, and fail-closed verification grouping.
- [x] Run the four tests and observe GREEN; characterization must not require production changes.
- [x] Mark the design plan complete and create one active foundation plan listing only Task 2–7 paths, a 45-file/4500-line branch ceiling, tests, Tach, and ADR. This includes generated reference/DocSync outputs while completed design artifacts remain governed by the completed design plan.
- [x] Commit: `test: characterize provider foundation seams`.

### Task 2: Add frozen nested Java configuration

**Files:**

- Create: `src/agent_maintainer/config/java.py`
- Modify: `src/agent_maintainer/config/schema.py`
- Modify: `src/agent_maintainer/config/{coercion,source_validation,loader,registry,schema_fields,validation,reference}.py`
- Create: `tests/config/test_java_config.py`
- Modify: `tests/config/test_{coercion,loading,validation,registry_validation}.py`

- [x] Write failing tests for defaults, a complete `[tool.agent_maintainer.java]`, `[[...java.reports]]`, unknown keys/types, invalid task syntax/paths/globs, forbidden Gradle arguments in split and `=` forms, and the sole env override `AGENT_MAINTAINER_JAVA_ENABLED`.
- [x] Run `.venv/bin/pytest tests/config/test_java_config.py -q`; verify RED because `MaintainerConfig.java` is absent.
- [x] Implement frozen `JavaReportExpectation` and `JavaGradleConfig`. Use tuple defaults and add `java: JavaGradleConfig = JavaGradleConfig()` to `MaintainerConfig`.
- [x] Add dedicated nested-table coercion and unknown-key validation; do not flatten Java topology into scalar field specs.
- [x] Structurally validate task names, profiles, relative paths/globs, and the argument allowlist while preserving a typed config when a selected tool has no tasks. Put that semantic readiness error in the provider/runner so doctor can diagnose it before verification fails.
- [x] Run the new and affected config tests; verify GREEN.
- [x] Commit: `feat: add Java Gradle configuration contract`.

### Task 3: Collect evidence and classify Java/Gradle paths

**Files:**

- Create: `src/agent_maintainer/ecosystems/java/{__init__,classification}.py`
- Modify: `src/agent_maintainer/assess/{models,evidence}.py`
- Modify: `src/agent_maintainer/ecosystems/registry.py`
- Create: `tests/ecosystems/test_java_classification.py`
- Modify: `tests/assess/test_evidence.py`
- Modify: `tests/catalogs/test_provider_registry.py`

- [x] Add failing cases for wrappers, Groovy/Kotlin build/settings files, catalogs, conventional/configured source and test roots, dependency files, generated/cache/report paths, and unconventional `.java` remaining unknown.
- [x] Run the focused tests; verify RED because Java evidence and candidate dispatch are missing.
- [x] Extend bounded Git-first evidence collection without running Gradle.
- [x] Add a Java classification candidate gated by `config.java.enabled`; reuse provider-neutral dispatch and roles.
- [x] Run focused tests; verify GREEN and existing Python/TypeScript classifiers unchanged.
- [x] Commit: `feat: classify Java Gradle repositories`.

### Task 4: Confine and resolve the checked-in wrapper

**Files:**

- Create: `src/agent_maintainer/ecosystems/java/wrapper.py`
- Create: `tests/ecosystems/test_java_wrapper.py`

- [x] Write failing tests for POSIX and Windows wrapper selection, missing/non-file/non-executable wrappers, `gradle_root` escape, and a symlink escaping the canonical repository.
- [x] Run `.venv/bin/pytest tests/ecosystems/test_java_wrapper.py -q`; verify RED due to missing module.
- [x] Implement `resolve_gradle_wrapper(workspace: Path, gradle_root: str) -> ResolvedGradleWrapper`, using canonical paths, regular-file checks, POSIX executable checks, and no PATH fallback.
- [x] Run the focused tests; verify GREEN.
- [x] Commit: `feat: confine Java Gradle wrapper resolution`.

### Task 5: Plan grouped provider checks

**Files:**

- Create: `src/agent_maintainer/ecosystems/java/provider.py`
- Modify: `src/agent_maintainer/ecosystems/registry.py`
- Create: `tests/ecosystems/test_java_provider.py`
- Create: `tests/catalogs/test_java_catalog.py`
- Modify: `tests/catalogs/test_provider_registry.py`

- [x] Write failing tests for disabled behavior, metadata after TypeScript, ordered de-duplicated tasks, selected tools without tasks producing an explicit verification configuration failure, group/profile mapping, command shape, and one bounded artifact path.
- [x] Run focused tests; verify RED because `JavaProvider` is absent.
- [x] Implement checks named `java-gradle-format`, `java-gradle-static`, and `java-gradle-tests`, invoking `sys.executable -m agent_maintainer.ecosystems.java.runner --group <group>`.
- [x] Append `JavaProvider()` after `TypeScriptProvider()` and set experimental metadata `enabled_field="java.enabled"`.
- [x] Run focused and characterization tests; verify GREEN.
- [x] Commit: `feat: register Java Gradle provider checks`.

### Task 6: Execute grouped checks hermetically

**Files:**

- Create: `src/agent_maintainer/ecosystems/java/runner.py`
- Create: `tests/ecosystems/test_java_runner.py`
- Create: `tests/fixtures/java_gradle/{groovy-single-project,kotlin-multi-project,custom-source-sets,missing-wrapper}/`

- [x] Write failing tests using fake wrappers that record argv/cwd and return controlled codes; assert no shell, exact `gradle_root` cwd, strict args, selected-tool readiness, group task ordering, exit propagation, and bounded sanitized JSON.
- [x] Run the runner tests; verify RED because the runner does not exist.
- [x] Implement config loading, group planning, wrapper resolution, `subprocess.run(..., shell=False)`, exit propagation, and atomic bounded artifact writing. Phase 1 artifact states execution only and does not claim reports were parsed.
- [x] Run focused tests; verify GREEN without network or a Gradle installation.
- [x] Commit: `feat: run grouped Gradle checks hermetically`.

### Task 7: Wire doctor, verification groups, architecture, and policy

**Files:**

- Modify: `src/agent_maintainer/doctor/{cli.py,support/providers.py,support/policy.py}`
- Modify: `src/agent_maintainer/verify/groups.py`
- Modify: `src/agent_maintainer/ecosystems/tach.domain.toml`
- Create: `tests/doctor/test_java_doctor.py`
- Modify: `tests/verify/test_verification_groups.py`
- Create: `docs/architecture/decisions/2026-07-16-java-gradle-provider-boundary.md`
- Modify: `docs/roadmap/{overview,polyglot-ecosystem-providers}.md`

- [x] Write failing tests for dotted provider enablement, disabled silence, static wrapper/runtime/config checks, proof normal doctor never invokes Gradle, and all three verification-group mappings.
- [x] Run focused tests; verify RED on dotted enablement/Java rows.
- [x] Add one tested dotted-path resolver, Java static doctor checks, and group mappings (`format`/`static` to static-and-policy, `tests` to tests-and-coverage).
- [x] Declare Java Tach modules/dependencies and add the required ADR; record built-in experimental status and forbidden boundaries.
- [x] Add the minimal truthful configuration/provider reference and DocSync trace required for Phase 1, with setup, reports, baselines, and coverage explicitly marked unavailable.
- [x] Run both focused command blocks from the Phase 1 validation spec, `just doctor`, then `just v`.
- [x] Commit: `feat: complete Java Gradle provider foundation`.

### Phase Gate

- [x] Confirm no report parser, baseline, setup template, JaCoCo threshold, live Gradle, or parity claim entered the diff.
- [x] Confirm one wrapper call per group and no `tasks --all` execution.
- [x] Record the Task 7 full-gate result before starting setup work.
