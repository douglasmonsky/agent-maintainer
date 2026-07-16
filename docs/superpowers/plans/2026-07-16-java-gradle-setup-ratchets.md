# Java/Gradle Setup and Native Ratchets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure deterministic Java/Gradle defaults and add safe native Spotless and SpotBugs ratchets without rewriting arbitrary builds.

**Architecture:** Java-owned defaults and templates create reviewed setup plans. Known scaffolds are deterministic; arbitrary Gradle builds use a typed agent-assisted semantic-edit handoff that previews and validates the diff or refuses safely. Spotless uses `ratchetFrom`; SpotBugs retains plugin-native XML baselines.

**Tech Stack:** Python, Gradle Groovy/Kotlin DSL templates, secure bounded XML, pytest.

## Global Constraints

- Preserve public setup modes: Recommended (automatic defaults), Guided (high-impact questions), Full control (every option).
- Pin versions and own curated rulesets; do not download during normal tests.
- Verification never creates or rewrites baselines.
- Gradle exit status remains authoritative.

---

### Task 1: Define pinned defaults and deterministic templates

**Files:** Create `src/agent_maintainer/ecosystems/java/defaults.py`; create `src/agent_maintainer/ecosystems/java/templates/**`; create `tests/ecosystems/java/test_{defaults,templates}.py`.

- [ ] Write failing snapshot/semantic tests for pinned plugins, SpotBugs effort/confidence, non-format Checkstyle/PMD rules, complexity 10/15/200, file ceilings 500/375, and coverage 80/70.
- [ ] Verify RED, implement immutable defaults and Groovy/Kotlin DSL fragments, then verify GREEN.
- [ ] Commit: `feat: add deterministic Java Gradle defaults`.

### Task 2: Build safe Java setup plans and semantic-edit handoffs

**Files:** Create `src/agent_maintainer/ecosystems/java/setup.py`; modify `src/agent_maintainer/core/setup_plans.py`; create `tests/ecosystems/java/test_setup.py`; create `tests/fixtures/java_gradle/{groovy_single,kotlin_multi}/**`.

- [ ] Write failing tests for new Java-only, mixed, single/multi-project, recognized scaffold edits, idempotence, preview/apply parity, typed semantic-edit requests/results for arbitrary builds, displayed diffs, validation results, and safe refusal on ambiguity.
- [ ] Verify RED, implement typed setup decisions, deterministic writes, and the agent-assisted handoff boundary; require a reviewed diff before applying any semantic-edit result, then verify GREEN.
- [ ] Commit: `feat: plan Java Gradle setup safely`.

### Task 3: Integrate evidence, advisor, and setup skill

**Files:** Modify `src/agent_maintainer/assess/{models,evidence,setup_advisor}.py`; modify `src/agent_maintainer/skill/resources/agent-maintainer-setup/SKILL.md`; modify `tests/assess/test_setup_advisor*.py`; modify `tests/skill/test_interaction_contract.py`.

- [ ] Write failing tests showing Java recommendations require concrete wrapper/build/source evidence and that all three existing modes explain Java choices.
- [ ] Verify RED, add bounded Gradle/module evidence and skill routing, then verify GREEN.
- [ ] Commit: `feat: guide Java Gradle repository setup`.

### Task 4: Validate Spotless native ratchets

**Files:** Modify `src/agent_maintainer/ecosystems/java/{setup,runner}.py`; create `tests/ecosystems/java/test_spotless_ratchet.py`; create established-repo fixtures.

- [ ] Write failing tests for explicit base refs, shallow/unavailable refs failing configuration, CI fetch guidance, and verification never applying formatting.
- [ ] Verify RED, implement `ratchetFrom` configuration/validation, then verify GREEN.
- [ ] Commit: `feat: enforce Spotless ratchet references`.

### Task 5: Observe Gradle tasks and reports safely

**Files:** Create `src/agent_maintainer/ecosystems/java/observations.py`; create `tests/ecosystems/java/test_gradle_observations.py`; modify `src/agent_maintainer/ecosystems/java/runner.py`.

- [ ] Write failing tests for task-scoped requested-task outcomes and pre-run report snapshots, including symlinked report matches escaping `gradle_root`.
- [ ] Verify RED, implement the shared `GradleObservation`/`ReportSnapshot` API used by all later report and baseline work, then verify GREEN.
- [ ] Commit: `feat: observe Gradle task evidence safely`.

### Task 6: Parse and create SpotBugs native baselines safely

**Files:** Create `src/agent_maintainer/ecosystems/java/reports/{__init__,xml,spotbugs}.py`; modify `src/agent_maintainer/ecosystems/java/{setup,runner}.py`; create `tests/ecosystems/java/test_{spotbugs_report,spotbugs_baseline,native_ratchet_runner}.py`.

- [ ] Write failing tests for DTD/entity rejection, byte/element/finding/message limits, malformed/incomplete/stale/failed task-scoped evidence, deterministic native XML creation, and verification immutability.
- [ ] Verify RED, implement bounded XML input and successful-complete-evidence baseline creation over the shared observation API, then verify GREEN.
- [ ] Commit: `feat: add safe SpotBugs native baselines`.

### Task 7: Orchestrate reviewed post-edit validation

**Files:** Modify `src/agent_maintainer/ecosystems/java/setup.py` and setup skill; create `tests/ecosystems/java/test_setup_validation.py`.

- [ ] Write failing tests for this exact opt-in sequence: wrapper/version check; show and approve `tasks --all`; observation-mode report tasks when baselining; baseline generation only after successful evidence; normal doctor; full verification.
- [ ] Implement the ordered plan while proving normal doctor and verification never perform task discovery.
- [ ] Commit: `feat: validate reviewed Java Gradle setup`.

### Task 8: Generate repository CI plans

**Files:** Extend Java setup/templates; create `tests/ecosystems/java/test_ci_setup.py`.

- [ ] Write failing tests for cache-aware `static-and-policy` and `tests-and-coverage` jobs, preserving the repository's CI framework/JDK convention, displaying workflow diffs, and fetching the configured Spotless ref.
- [ ] Implement reviewed workflow plans with safe refusal for unknown CI structures; do not overwrite arbitrary workflows.
- [ ] Commit: `feat: plan Java Gradle verification CI`.

### Task 9: Close the setup/native-ratchet gate

**Files:** Modify relevant doctor/docs/config reference tests; add a phase-specific cohesive change plan.

- [ ] Add doctor checks for ratchet refs and baseline paths without executing Gradle.
- [ ] Update setup/config public docs and DocSync evidence for behavior introduced in this phase.
- [ ] Run all Phase 2/3 focused tests, `just doctor`, and `just v`.
- [ ] Confirm arbitrary existing builds are never regex-rewritten and no Checkstyle/PMD debt baseline appears yet.
- [ ] Commit: `docs: complete Java setup and native ratchet gate`.
