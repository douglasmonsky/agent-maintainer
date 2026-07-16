# Java/Gradle Coverage and Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add truthful JaCoCo ratchets, parallel cached live Gradle validation, public documentation, and calibrated Java-only/multi-project dogfood evidence.

**Architecture:** Parse JaCoCo XML with exact decimal arithmetic, keep base thresholds in `gradle.properties`, and reject downward changes. Reuse existing verification groups and protected aggregate CI while a separate experimental workflow runs cached live Gradle fixtures.

**Tech Stack:** Python Decimal, JaCoCo XML, GitHub Actions, Gradle wrapper/cache, DocSync, pytest.

## Global Constraints

- Default new repositories to line 80% and branch 70%; established floors round down to whole percentages.
- Multi-project coverage is aggregate only with a real aggregate report; otherwise label every project separately.
- Precommit uses at most one wrapper call; full/CI at most two.
- Do not claim parity before all promotion gates pass.

---

### Task 1: Parse JaCoCo and compare thresholds exactly

**Files:** Create `src/agent_maintainer/ecosystems/java/reports/jacoco.py`; extend Java baseline policy; create `tests/ecosystems/java/test_{jacoco_report,jacoco_thresholds}.py`.

- [x] Write failing tests for counters, zero denominators, malformed/oversized XML, four-decimal-place `Decimal` percentages, default floors, established rounding, and rejection of downward `gradle.properties` changes.
- [x] Implement an explicit base-ref reader that loads the configured line/branch property names from current and base `gradle.properties`, fails when required base data is unavailable, and reports XML headroom separately. Keep this policy outside the Java findings baseline.
- [x] Commit: `feat: add JaCoCo coverage ratchets`.

### Task 2: Enforce truthful single/multi-project coverage

**Files:** Modify Java defaults/templates/setup/runner; add single aggregate and multi-project/per-project fixtures; create `tests/ecosystems/java/test_jacoco_topology.py`.

- [x] Write failing tests for aggregate evidence, explicit per-project reports, missing modules, labels, report expectations, and task ordering.
- [x] Verify RED, implement topology validation with no synthetic repository-wide percentage, then verify GREEN.
- [x] Commit: `feat: report Gradle project coverage truthfully`.

### Task 3: Split and cache live Java CI

**Files:** Create `.github/workflows/java-gradle-live.yml`; modify `.github/workflows/{verify,deep-verify}.yml` only where group wiring requires it; modify `tests/packaging/test_parallel_verify_workflow.py`; create `tests/live/java_gradle/**`.

- [x] Write failing workflow tests for protected aggregate job `verify`, Java static/tests group placement, wrapper validation, dependency caching, offline-friendly fixtures, bounded timeouts, artifact upload, and explicit Linux/Windows matrix coverage.
- [x] Verify RED, add a separate cached experimental live workflow/nightly Linux/Windows matrix, then verify GREEN.
- [x] Run live Groovy and Kotlin DSL fixtures with the checked wrappers; record wrapper calls and runtime.
- [x] Commit: `ci: validate live Java Gradle fixtures in parallel`.

### Task 4: Calibrate on representative repositories

**Files:** Create `docs/case-studies/java-gradle-provider-calibration.md`; create sanitized Java-only, mixed Python/Java, and multi-project evidence fixtures; create `tests/assess/test_java_real_repo_calibration.py`.

- [x] Capture sanitized false positives, setup diff/manual edits, runtime/wrapper calls, repair-fact usefulness, baseline churn, and coverage labeling for Java-only, mixed Python/Java, and multi-project repositories.
- [x] Add failing tests for the evidence schema and required cases, then implement fixtures/report until GREEN.
- [x] Tune new-repo defaults separately from established ratchets; never silently lower enforcement.
- [x] Commit: `test: calibrate Java Gradle provider behavior`.

### Task 5: Document and trace the experimental provider

**Files:** Create `docs/java-gradle-provider.md`; modify `README.md`, provider/setup/config/agent-use/roadmap docs, `.docsync/trace.yml`, and doc tests.

- [ ] Write failing docs/DocSync tests requiring status, wrapper/config/setup modes, ratchets, baselines, topology, CI, limitations, and repair workflow.
- [ ] Update public docs without parity claims, then run docs tests and DocSync until GREEN.
- [ ] Commit: `docs: document experimental Java Gradle support`.

### Task 6: Run promotion and completion audit

- [ ] Run the complete Phase 6 test list, `python -m docsync doctor`, `python -m docsync check --base origin/main`, `just doctor`, `just vc`, and `just v`.
- [ ] Audit wrapper-call budgets, no `tasks --all`, no system Gradle fallback, no baseline mutation during verification, no unsafe XML, no compatibility shims, and clean provider ordering.
- [ ] Perform one independent full-branch review against all three specs; fix findings test-first and rerun impacted/full gates.
- [ ] Mark the implementation plan complete only when every promotion gate has current evidence; keep the provider experimental otherwise.
- [ ] Commit: `feat: complete experimental Java Gradle rollout`.
