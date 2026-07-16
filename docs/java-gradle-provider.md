<!-- docsync:object docs.java_gradle_provider.overview -->
# Experimental Java/Gradle Provider

Agent Maintainer has a built-in experimental Java/Gradle provider for
repositories that own explicit Gradle tasks and a checked-in Gradle wrapper.
It adds structured, ratcheted maintenance without hiding build behavior behind
an Agent Maintainer Gradle plugin or a system Gradle installation.

The provider is useful for new repositories today, but experimental still
means configuration may evolve and Python remains the core/reference provider.
Completing this rollout does not claim Python feature parity or stable-provider
status.

## Prerequisites

Enable the provider only when the repository has:

- `gradlew`, `gradlew.bat`, and a validated wrapper JAR;
- a Groovy or Kotlin DSL build beneath one explicit `gradle_root`;
- repository-owned task names for every enabled tool;
- stable XML report paths for structured evidence;
- a Git base reference available wherever an upward-only ratchet is evaluated.

Agent Maintainer does not fall back to system Gradle. Maven is not supported,
and verification never discovers or guesses task names.

## Setup modes

The setup skill offers Recommended, Guided, or Full control:

- Recommended applies evidence-backed defaults to a recognized new scaffold.
- Guided asks only questions that repository evidence cannot answer safely.
- Full control walks through every supported choice and its trade-off.

All modes display a deterministic reviewed diff. Recognized scaffolds receive
provider-owned Groovy or Kotlin fragments, `gradle.properties` coverage floors,
and Checkstyle/PMD rulesets. Arbitrary existing builds receive a typed semantic
edit request; Agent Maintainer never uses a regex rewrite. Apply requires the
same reviewed digest and rejects stale source.

Setup-only task discovery may run `tasks --all` after the user approves the
displayed command. Doctor and normal verification never run it.

## Minimal configuration

```toml
[tool.agent_maintainer.java]
enabled = true
gradle_root = "."
checks = ["spotless", "spotbugs", "checkstyle", "pmd", "test", "jacoco"]
projects = [":"]

spotless_tasks = ["spotlessCheck"]
spotbugs_tasks = ["spotbugsMain", "spotbugsTest"]
checkstyle_tasks = ["checkstyleMain", "checkstyleTest"]
pmd_tasks = ["pmdMain", "pmdTest"]
test_tasks = ["test"]
jacoco_report_tasks = ["jacocoTestReport"]
jacoco_verify_tasks = ["jacocoTestCoverageVerification"]

spotless_ratchet_ref = "origin/main"
jacoco_ratchet_ref = "origin/main"
spotbugs_baseline = "config/spotbugs/baseline.xml"
findings_baseline = ".agent-maintainer/java-findings-baseline.json"

[[tool.agent_maintainer.java.reports]]
tool = "jacoco"
tasks = ["jacocoTestReport"]
globs = ["build/reports/jacoco/test/jacocoTestReport.xml"]
coverage_scope = "project"
coverage_label = ":"
```

The complete defaults and nested key inventory are generated in the
[configuration reference](configuration-reference.md).

## Profiles and wrapper-call budgets

The provider exposes format, static, and tests groups. Spotless may run in
`precommit`, `full`, and `ci`; static and tests groups normally run in `full`
and `ci`. Task order is deterministic and duplicate task names are removed
without reordering the first occurrence.

Precommit uses at most one wrapper call. Full and CI use at most two wrapper
calls: one for static analysis and one for tests plus coverage. Agent Maintainer
passes task arguments directly to the checked wrapper without a shell, confines
execution to `gradle_root`, caps output, and records exact task outcomes.

## Ratchets and baselines

New repositories start at 80% line and 70% branch coverage. Established floors
round down to whole percentages during reviewed calibration, then remain
upward-only. The configured `jacoco_ratchet_ref` supplies base
`gradle.properties`; missing base data, malformed ratios, or any downward
change fails closed. XML headroom is reported separately and never authorizes
lowering a stored floor.

Spotless `ratchetFrom` also requires an explicit available Git reference. It
never fetches a missing reference or expands into a whole-repository format
operation.

A native SpotBugs baseline is a repository-owned `FindBugsFilter`. Creation
requires complete, fresh, successful report evidence at the current clean Git
commit. Normal verification and doctor never create or mutate it.

Normalized Checkstyle, PMD, and SpotBugs debt uses the explicit
`assess java-baseline create|inspect|prune` lifecycle. Provider-neutral file
ceilings remain a separate baseline. Verification compares all of these
artifacts but never updates them.

## Truthful coverage topology

Single-project coverage is a project fact labeled `:`. Multi-project coverage
must use one of two honest shapes:

1. exactly one real aggregate report with `coverage_scope = "aggregate"`; or
2. separate labeled project facts for every configured entry in `projects`.

Agent Maintainer rejects missing, duplicate, unknown, or mixed labels. It never
adds project percentages together and never invents a repository-wide number.
When no real aggregate report exists, configure fully qualified tasks and one
report path per project.

## Structured evidence and repair workflow

The runner accepts bounded Checkstyle, PMD, SpotBugs, JUnit, and JaCoCo XML.
Reports must be fresh, confined beneath the Gradle root, mapped to successful
tasks, within size/element/finding limits, and complete. Raw XML remains in
Gradle build output; the runner artifact contains only sanitized facts.

After a failure, start with bounded context:

```bash
python -m agent_maintainer context failures --limit 20
python -m agent_maintainer repair-plan
```

Use the reported run ID and expand only the failed Java check when more detail
is needed. Fix the source or build configuration, rerun the smallest affected
group, then run `full` or `ci`. Create or prune a baseline only through its
explicit command after reviewing the diff; do not edit verifier output into a
new baseline.

## CI evidence

Reviewed repository CI plans preserve the selected JDK distribution/version
and place Java static analysis in `static-and-policy` and tests/coverage in
`tests-and-coverage`. They refuse unknown CI frameworks and never overwrite an
unrecognized workflow.

Agent Maintainer's path-filtered/nightly matrix is configured to run checked
Gradle 9.6.1 Groovy and Kotlin DSL fixtures on Linux and Windows. It validates
every wrapper JAR and executes the real static and tests groups through Agent
Maintainer. The fixtures exercise native Spotless ratcheting, a SpotBugs native
baseline, Checkstyle, PMD, JUnit, JaCoCo, and bounded XML evidence in exactly two
wrapper calls. The workflow uses a bounded Gradle dependency cache, enforces a
20-minute job timeout, records calls/runtime, and uploads reports plus sanitized
runner artifacts. It stays separate from the protected aggregate `verify` job.

## Current limitations

- Java support remains experimental and disabled by default.
- Maven is not supported; only one explicit Gradle root is configured at a
  time.
- Task and report discovery is setup-only, reviewed, and never part of normal
  verification.
- Multi-project aggregate coverage requires a real aggregate report; synthetic
  aggregation is deliberately unsupported.
- Java does not yet receive all Python-specific blocking reviewability,
  mutation, dependency, security, or test-intelligence gates.
- The calibrated fixtures are small controlled repositories, not production
  performance benchmarks.

See [Provider Status](provider-status.md), the
[Java/Gradle Provider Calibration](case-studies/java-gradle-provider-calibration.md),
and [Setup Advisor](setup-advisor.md) for maturity and adoption context.
<!-- docsync:object.end docs.java_gradle_provider.overview -->
