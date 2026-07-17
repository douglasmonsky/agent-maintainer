# Java and Gradle Validation and Rollout

Date: 2026-07-15
Status: approved companion to the Java and Gradle support design

This document is the normative validation and delivery companion to
[Java and Gradle Support Design](2026-07-15-java-gradle-support-design.md).

## Testing Strategy

### Unit tests

- Nested config parsing, validation, unknown keys, and profile membership.
- POSIX and Windows wrapper resolution, executable checks, and symlink escapes.
- Task grouping, ordering, de-duplication, and command injection rejection.
- Java/Gradle file classification and custom roots.
- XML parser limits and malicious or malformed inputs.
- Finding normalization, multiset matching, numeric ratchets, and pruning.
- JaCoCo threshold non-regression.
- Doctor states and setup-advisor evidence.
- Disabled-provider silence.
- Python and TypeScript provider characterization.

### Hermetic integration fixtures

- Groovy DSL single-project new repository.
- Kotlin DSL multi-project new repository.
- Established repository with every baseline type.
- Custom source sets and fully qualified tasks.
- Gradle failure with partial reports.
- Zero exit with a missing or malformed required report.
- Moved lines, duplicate findings, improved complexity, and worsened complexity.
- Missing wrapper, non-executable wrapper, and unavailable ratchet reference.

Hermetic fixtures use fake wrappers and checked-in report samples. They do not
depend on network plugin downloads.

### Live Gradle fixtures

Pinned live fixtures prove both DSLs, task wiring, native Spotless and SpotBugs
ratchets, XML generation, JaCoCo verification, and grouped execution. They run
outside the fast unit-test lane with Gradle dependency caching.

### Performance acceptance

- Precommit starts at most one Gradle invocation.
- Full and CI start at most two.
- Normal verify never calls `tasks --all`.
- Report parsing is linear and bounded.
- No forced clean or cache invalidation occurs.
- Static and tests/coverage can run as independent CI groups.

## Documentation and Architecture Updates

Implementation updates:

- `docs/java-gradle-provider.md`.
- Provider status and contribution guide.
- Setup advisor and configuration reference.
- Supported scans and agent-use documentation.
- Multi-ecosystem policy and roadmap sequencing.
- DocSync trace and evidence for public claims.
- `src/agent_maintainer/ecosystems/tach.domain.toml`.
- README ecosystem summary after the first usable phase.

The planned ecosystems Tach policy update requires an ADR in Phase 1. Any later
change to the private provider boundary or public configuration stability policy
requires its own explicit ADR decision.

## Phased Delivery

### Phase 0: policy and characterization

- Record the Java priority and superseded TypeScript-first sequence.
- Pin Python, TypeScript, catalog, config, doctor, and verifier behavior with
  characterization tests before modifying shared seams.

### Phase 1: provider skeleton

- Add Java evidence, classification, nested config, registry metadata, wrapper
  resolution, grouped explicit-task checks, doctor basics, and hermetic fixtures.
- Record the ecosystems Tach policy change in an ADR.
- Make no report-baseline claims yet.

### Phase 2: setup and deterministic defaults

- Add both DSL templates, the tested version manifest, rulesets, setup-plan
  output, task validation, and setup-skill integration.
- Prove new-repository zero-debt operation with live fixtures.

### Phase 3: native ratchets

- Add Spotless base-reference handling and SpotBugs baseline generation.
- Add the bounded SpotBugs XML validation needed to refuse unsafe, malformed,
  truncated, or failed baseline evidence.
- Add CI history checks and native-ratchet failure fixtures.

### Phase 4: structured debt baselines

- Extend SpotBugs parsing into normalized facts and add bounded Checkstyle, PMD,
  and JUnit parsing.
- Add finding fingerprints, complexity comparison, file-size ceilings, baseline
  create/inspect/prune operations, and structured repair artifacts.

### Phase 5: coverage and CI optimization

- Add JaCoCo XML facts and upward-only Gradle property checks.
- Add parallel verification guidance, live fixture CI, and timing evidence.

### Phase 6: real-repository calibration

- Dogfood on at least one Java-only and one multi-project repository.
- Record false positives, setup edits, runtime, repair usefulness, and baseline
  churn.
- Tune defaults without silently weakening established repository behavior.

## Phase Exit Gates

Every phase must:

- pass its targeted tests and the repository's standard verification gate;
- preserve Python and TypeScript characterization tests;
- update config and public documentation for behavior introduced in that phase;
- update Tach and DocSync evidence when their governed boundaries change;
- leave later-phase behavior explicitly unsupported rather than partially
  emulated;
- receive an independent code review before the next phase begins.

## Provider Promotion Gates

Java remains experimental until all of the following are true:

- Both Gradle DSLs pass hermetic and live fixtures.
- Linux and Windows wrapper behavior is proven.
- Java-only and mixed repositories pass setup and verification.
- A multi-project repository uses fully qualified tasks successfully.
- Native and external ratchets have regression fixtures.
- Missing and malformed reports fail closed.
- Python and TypeScript behavior remains unchanged.
- Setup produces reviewable, reversible changes without restructuring builds.
- Full verification uses at most two wrapper calls with acceptable CI timing.
- Real-repository evidence shows tolerable false positives and baseline churn.
- Provider docs and DocSync evidence make no unsupported parity claims.

Promotion to supported or stable requires a separate decision. It is not
automatic when the implementation phases finish.

## Alternatives Rejected

### Command-only provider

Copying the TypeScript provider cannot provide structured Java repair facts,
existing-debt comparison, or meaningful quality ratchets.

### Agent Maintainer Gradle plugin or init script

This creates hidden build behavior, Gradle compatibility obligations, and a
second plugin product.

### Gradle Tooling API discovery

This adds JVM integration, daemon lifecycle, and version compatibility
complexity before the provider seam is proven.

### Maven and Gradle together

Supporting both would blur the first provider boundary and double setup,
fixture, execution, and report-path concerns. Maven follows only after Gradle
evidence exists.
