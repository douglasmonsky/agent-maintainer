# Java and Gradle Runtime Contracts

Date: 2026-07-15
Status: approved companion to the Java and Gradle support design

This document is the normative configuration and execution companion to
[Java and Gradle Support Design](2026-07-15-java-gradle-support-design.md).

## Typed Configuration

The public TOML surface is provider-owned:

```toml
[tool.agent_maintainer.java]
enabled = true
gradle_root = "."
checks = ["spotless", "spotbugs", "checkstyle", "pmd", "test", "jacoco"]
gradle_args = ["--console=plain", "--continue"]
source_roots = ["src/main/java", "**/src/main/java"]
test_roots = ["src/test/java", "**/src/test/java"]
projects = [":"]

spotless_tasks = ["spotlessCheck"]
spotbugs_tasks = ["spotbugsMain", "spotbugsTest"]
checkstyle_tasks = ["checkstyleMain", "checkstyleTest"]
pmd_tasks = ["pmdMain", "pmdTest"]
test_tasks = ["test"]
jacoco_report_tasks = ["jacocoTestReport"]
jacoco_verify_tasks = ["jacocoTestCoverageVerification"]

spotless_profiles = ["precommit", "full", "ci"]
spotbugs_profiles = ["full", "ci"]
checkstyle_profiles = ["full", "ci"]
pmd_profiles = ["full", "ci"]
test_profiles = ["full", "ci"]
jacoco_profiles = ["full", "ci"]

spotless_ratchet_ref = "origin/main"
findings_baseline = ".agent-maintainer/java-findings-baseline.json"
spotbugs_baseline = "config/spotbugs/baseline.xml"
jacoco_ratchet_ref = "origin/main"
jacoco_line_property = "agentMaintainer.jacoco.minimumLineCoverage"
jacoco_branch_property = "agentMaintainer.jacoco.minimumBranchCoverage"

[[tool.agent_maintainer.java.reports]]
tool = "checkstyle"
tasks = ["checkstyleMain", "checkstyleTest"]
globs = ["build/reports/checkstyle/main.xml", "build/reports/checkstyle/test.xml"]
required = true
```

Multi-project tasks may be fully qualified. Setup emits one or more report
expectations per tool/module when conventional single-project defaults are
insufficient.

The example includes established-repository ratchet paths. New repositories
omit `spotless_ratchet_ref` and `spotbugs_baseline` until those native baseline
features are intentionally enabled.

The frozen `JavaGradleConfig` contains exactly:

- `enabled`, `gradle_root`, `checks`, and `gradle_args`;
- production and test root patterns;
- the ordered Gradle project labels covered by project-scoped reports;
- tasks and profiles for each supported tool;
- Spotless ratchet reference and both baseline paths;
- JaCoCo ratchet reference plus line and branch property names;
- an ordered tuple of `JavaReportExpectation` values.

Each report expectation contains `tool`, `tasks`, repository-confined `globs`,
`required`, `coverage_scope`, and `coverage_label`. Coverage fields are empty for
non-JaCoCo reports. The default single-project expectations cover SpotBugs,
Checkstyle, PMD, JUnit, and project-scoped JaCoCo XML labeled `:`. Spotless has
no report expectation.

`MaintainerConfig` owns one `java: JavaGradleConfig` field. Provider metadata
keeps the enablement string `java.enabled`; `provider_enabled` resolves direct
and dotted field paths through one shared helper. Existing direct fields such as
`enable_typescript` retain their current behavior without aliases or migration.

The nested-table parser rejects unknown keys and invalid types. Java task arrays
do not receive shell/environment coercion. The first release exposes only
`AGENT_MAINTAINER_JAVA_ENABLED`; task topology remains committed repository
configuration.

## Profile Matrix

V1 permits:

- Spotless in any subset of `precommit`, `full`, and `ci`.
- SpotBugs, Checkstyle, and PMD in any subset of `full` and `ci`.
- Tests and JaCoCo in any subset of `full` and `ci`.

Other assignments are configuration errors. A selected tool without tasks is a
doctor warning and a verification configuration failure. An unselected tool is
silent and contributes no task, report expectation, or skip result.

## Path and Wrapper Confinement

`gradle_root` is relative to the canonical Agent Maintainer workspace and must
resolve inside it. Report globs are relative to `gradle_root`; baseline files and
source-root patterns are relative to the canonical workspace. Every resolved
path is checked again after symlink resolution.

The wrapper resolver:

1. chooses `gradlew.bat` on Windows and executable `gradlew` on POSIX;
2. requires the wrapper to be a regular file under `gradle_root`;
3. rejects symlink escapes and absolute external paths;
4. treats a non-executable POSIX wrapper as a setup error;
5. never searches `PATH` for `gradle`.

The subprocess working directory is exactly `gradle_root`, not the parent
workspace root. This preserves Gradle settings and relative build behavior when
the Gradle build occupies a repository subdirectory.

## Argument and Task Validation

`gradle_args` is a strict allowlist in V1:

- `--console=plain`;
- `--continue`;
- `--stacktrace`;
- `--offline`;
- `--warning-mode=all|fail|summary|none`;
- `--max-workers=N`, where `N` is a bounded positive integer.

All other arguments fail validation until deliberately added with tests. In
particular V1 rejects project, settings, build-file, init-script, included-build,
Gradle-user-home, project-cache, dependency-verification, property, and system-
property flags in both long and short forms. Paired values and `--flag=value`
forms are normalized before validation so a forbidden path cannot hide in the
next token.

Task identifiers must match Gradle's colon-qualified task-name grammar, may not
begin with `-`, and may not contain whitespace or shell metacharacters. No shell
is involved in execution.

## Check Planning

The provider emits:

| Check | Profiles | Contents |
| --- | --- | --- |
| `java-gradle-format` | `precommit` | configured Spotless tasks |
| `java-gradle-static` | `full`, `ci` | Spotless, SpotBugs, Checkstyle, PMD |
| `java-gradle-tests` | `full`, `ci` | tests and JaCoCo |

The planner derives ordered, de-duplicated task arrays for each permitted
profile. If a tool is omitted from a profile, its tasks and reports are omitted.
`java-gradle-static` belongs to static-and-policy;
`java-gradle-tests` belongs to tests-and-coverage.

The provider never adds `clean`, `--rerun-tasks`, or `--no-daemon`. It honors
repository daemon, cache, parallel, and configuration-cache settings and does
not force `--parallel` or `--configuration-cache`. Normal verification never
runs `tasks --all`.

## Subprocess Runner Protocol

The existing executor remains command-only. Each grouped `Check.command` runs:

```text
python -m agent_maintainer.ecosystems.java.runner --group <group>
```

The runner loads the same validated repository config, invokes the wrapper, and
returns the final policy result through its process exit status. The `Check`
declares the runner's bounded JSON output through existing `artifact_paths`.
No callback, callable field, or Java branch is added to the core executor.

The runner:

1. resolves the wrapper and grouped task array;
2. snapshots matching report paths and digests;
3. invokes Gradle from `gradle_root` with plain console output;
4. parses requested-task outcomes;
5. validates report expectations and freshness;
6. parses findings and compares baselines;
7. writes one sanitized structured artifact;
8. exits nonzero for any Gradle, evidence, or policy failure.

Raw third-party reports remain in Gradle output. They are not copied into Agent
Maintainer run history.

## Task Outcomes and Report Freshness

The runner recognizes outcomes for every requested task:

| Gradle outcome | Required evidence |
| --- | --- |
| Executed successfully | every required report exists and is newly written |
| `FROM-CACHE` | every required cached report exists |
| `UP-TO-DATE` | every required existing report exists |
| `NO-SOURCE` | no report required; emit a no-source fact |
| `SKIPPED` | configuration failure in V1 |
| Failed | preserve failure; parse available reports only for diagnostics |
| Requested task absent from output | configuration failure |

`NO-SOURCE` for the configured test task is still a failure when the repository
requires tests. Setup omits analyzer tasks for source sets known to be empty.

Plain Gradle task lines are parsed only to establish these outcomes. An unknown
or ambiguous outcome fails closed. Report expectations are task-scoped so one
module's old report cannot satisfy another module's task. Pre-run report digests
are retained in the structured artifact for evidence, but unchanged output is
accepted only for an explicit `UP-TO-DATE` outcome.

## Multi-Project JaCoCo

Single-project defaults use the normal `jacocoTestReport` and
`jacocoTestCoverageVerification` tasks. Multi-project automatic setup configures
an explicit aggregate report and verification task when the build accepts that
change. Its task names and report are recorded exactly like any other
expectation.

If aggregation is declined, setup records per-project report and verification
tasks. Findings and thresholds are labeled per project; no repository-wide
coverage claim is produced. Line and branch properties use decimal values with
four-digit parsing precision. Existing floors are rounded down to the nearest
whole percentage point before being written.

## Failure Precedence

1. Invalid config, unsafe path/argument, or missing wrapper.
2. Gradle failure or missing requested task outcome.
3. Missing, stale, ambiguous, or malformed required evidence.
4. New or worsened debt.
5. Advisory improvements and baseline-pruning suggestions.

A selected tool with incomplete setup never becomes an optional passing skip.
