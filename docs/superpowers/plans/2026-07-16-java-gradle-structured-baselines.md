# Java/Gradle Structured Baselines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Java reports into bounded repair facts, deterministic multiset debt ratchets, and provider-neutral per-path file ceilings.

**Architecture:** Java owns report adapters, finding identity, and its findings baseline. The runner preserves Gradle authority while validating fresh expected evidence. File ceilings extend the existing provider-neutral subsystem once and remain separate from Java findings.

**Tech Stack:** Python dataclasses, secure XML, JSON schemas, Decimal-free integer findings, pytest/property tests.

## Global Constraints

- Normalize paths/messages deterministically and compare duplicate findings as a multiset.
- Moved lines must not create debt; changed rule/path/semantic subject must.
- Never let report parsing turn a failed Gradle run into a pass.
- Baseline mutation is explicit create/inspect/prune only.

---

### Task 1: Define canonical Java findings and baseline schema

**Files:** Create `src/agent_maintainer/ecosystems/java/{findings,baseline}.py`; create `tests/ecosystems/java/test_{findings,finding_baseline}.py`.

- [ ] Write failing tests for normalization, stable fingerprints across line moves, semantic changes, duplicates, deterministic JSON, provenance, create/inspect/prune, and numeric complexity ceilings.
- [ ] Verify RED, implement frozen `JavaFinding`, SHA-256 identity, `Counter` comparison, and versioned baseline I/O, then verify GREEN.
- [ ] Commit: `feat: add Java finding debt baselines`.

### Task 2: Add bounded Checkstyle, PMD, SpotBugs, and JUnit adapters

**Files:** Create `reports/{checkstyle,pmd,junit}.py`; modify `reports/spotbugs.py`; create `tests/ecosystems/java/test_{checkstyle,pmd,junit,spotbugs_report}.py`; add malicious/malformed fixtures.

- [ ] Write failing parser tests for valid dialects, warnings/errors, modules, absent optional fields, truncation, DTD/entities, oversized input, and malformed/incomplete reports.
- [ ] Verify RED, implement adapters over the single bounded XML primitive, then verify GREEN.
- [ ] Commit: `feat: parse bounded Java quality reports`.

### Task 3: Enforce report expectations and freshness in the runner

**Files:** Modify `src/agent_maintainer/ecosystems/java/runner.py`; modify `src/agent_maintainer/ecosystems/java/provider.py`; create `tests/ecosystems/java/test_report_outcomes.py` and `test_report_runner.py`.

- [ ] Write failing task-scoped matrix tests: `EXECUTED` requires newly written reports; `FROM-CACHE`/`UP-TO-DATE` accept existing complete reports; `NO-SOURCE` requires no report but still fails when configured tests are required; `SKIPPED`, absent requested tasks, unknown, and ambiguous outcomes fail closed. Include required globs, unmatched globs, pre-run snapshots, stale reports, and missing evidence.
- [ ] Add symlink-escape tests proving every glob match is resolved beneath `gradle_root` before parsing; unsafe or escaped matches fail closed.
- [ ] Reuse and extend the shared observation API, applying precedence: Gradle failure first, then requested-task outcome, confinement/freshness, parser completeness, findings comparison, and sanitized artifact emission.
- [ ] Commit: `feat: validate Java Gradle report evidence`.

### Task 4: Publish exact repair facts

**Files:** Create `src/agent_repair_facts/parsers/java.py`; modify `src/agent_repair_facts/registry.py`; modify `src/agent_maintainer/core/structured_artifacts.py`; create `tests/context/test_java_exact_facts.py`.

- [ ] Write failing tests for registry discovery, one bounded artifact read, concise findings/test summaries, path confinement, truncation, and malformed artifacts.
- [ ] Verify RED, register the Java artifact parser and summary, then verify GREEN.
- [ ] Commit: `feat: expose Java repair facts`.

### Task 5: Add explicit Java baseline lifecycle CLI

**Files:** Modify `src/agent_maintainer/assess/cli.py`; create `tests/assess/test_java_baseline_cli.py`; update configuration reference docs.

- [ ] Write failing CLI tests for `assess java-baseline create|inspect|prune`, successful-evidence requirement, dry-run output, deterministic writes, and nonzero invalid/stale input.
- [ ] Verify RED, route the commands to Java baseline operations without aliases, then verify GREEN.
- [ ] Commit: `feat: manage Java finding baselines explicitly`.

### Task 6: Extend provider-neutral per-path file ceilings

**Files:** Modify `src/agent_maintainer/config/{schema,registry,coercion,source_validation,validation,reference}.py`; modify `src/agent_maintainer/assess/file_baselines.py`; modify `tests/assess/test_file_baselines.py` and affected config tests.

- [ ] Write failing tests for versioned per-path physical/nonblank ceilings, new-file defaults, established floors, regression blocking, improvement suggestions, renamed/removed paths, create/inspect/prune, and Java/Python neutrality.
- [ ] Verify RED, implement the single provider-neutral comparator/lifecycle, then verify GREEN.
- [ ] Commit: `feat: enforce provider-neutral file ceilings`.

### Task 7: Close the structured-evidence gate

- [ ] Update baseline/report/artifact public docs and DocSync evidence for this phase.
- [ ] Run all Java ecosystem tests, file-baseline/check-file tests, config nested-table tests, exact-fact safety tests, `just doctor`, and `just v`.
- [ ] Confirm raw Gradle XML remains in build output, persisted artifacts are bounded/sanitized, and findings/file baselines remain separate.
- [ ] Commit the phase plan completion and verification evidence.
