# Java and Gradle Support Design

Date: 2026-07-15
Status: approved conversational design

## Context

Agent Maintainer is Python-core today and has one experimental
TypeScript/JavaScript provider. The internal provider seam already separates
check generation, file classification, doctor metadata, and structured repair
facts from the core verifier. Java support should extend that seam rather than
add Java assumptions to Python checks or create a public plugin API.

The current multi-ecosystem policy says to mature TypeScript before adding
another ecosystem. This design deliberately supersedes that sequencing because
Java support is now a priority for the maintainer's future repositories. It does
not promote TypeScript, weaken Python behavior, or change the provider maturity
model.

Gradle remains the build authority. Agent Maintainer configures and invokes the
repository's checked-in wrapper, consumes standard reports, and enforces debt
ratchets. It does not reproduce Gradle source sets, dependency resolution,
classpath construction, compilation, formatting, or analyzer behavior.

## Goals

- Support Java-only and mixed Python/Java repositories.
- Support single-project and multi-project Gradle builds from one Gradle root.
- Support both Groovy and Kotlin Gradle DSLs.
- Configure and run Spotless, SpotBugs, Checkstyle, PMD, tests, and JaCoCo.
- Give new repositories strict zero-debt defaults.
- Let established repositories baseline existing debt while blocking new or
  worsened findings.
- Reuse the existing provider registry, check executor, verification groups,
  artifacts, doctor, setup advisor, and provider-neutral file classification.
- Produce bounded structured repair facts rather than relying only on Gradle
  console output.
- Keep local and CI execution fast enough for routine use.
- Keep the provider built-in and experimental until real-repository evidence
  satisfies explicit promotion gates.

## Non-Goals

- Maven support.
- Android, Kotlin, Scala, or Groovy source analysis.
- Multiple independent Gradle roots or composite builds with separately owned
  wrappers in one Agent Maintainer workspace.
- Gradle Tooling API integration.
- A custom Agent Maintainer Gradle plugin or hidden init script.
- External provider discovery or a stable public provider API.
- Replacing repository-specific rulesets, test frameworks, or Gradle
  conventions during setup.
- Inferring arbitrary task names during normal verification.
- Falling back to a system-installed `gradle` executable.
- Compatibility aliases for abandoned Java config shapes.

## Design Principles

1. The checked-in wrapper is the only Gradle execution boundary.
2. Tasks and arguments are structured arrays, never shell strings.
3. Static assessment does not execute Gradle.
4. Setup may probe Gradle only after showing the proposed operation.
5. Gradle failures remain failures; reports may add failures but never erase
   them.
6. Native ratchets are preferred when their semantics match the policy.
7. Agent Maintainer baselines are used only where the Gradle plugin lacks a
   suitable debt baseline.
8. Verification never rewrites a baseline or build file.
9. Provider-specific knowledge remains under the Java ecosystem package.
10. Python remains the core/reference provider.

## Supported Repository Shape

V1 supports one canonical Gradle root containing:

- `gradlew` and/or `gradlew.bat`;
- `settings.gradle` or `settings.gradle.kts`;
- one or more Gradle projects;
- Java source sets with explicit configured tasks;
- `build.gradle`, `build.gradle.kts`, version catalogs, or convention plugins.

Standard `src/main/java` and `src/test/java` roots are detected automatically.
Setup records custom source sets and fully qualified tasks such as
`:service:spotbugsMain`. Included builds with their own wrappers require
separate Agent Maintainer workspaces and are outside V1.

## Architecture

The new package is `src/agent_maintainer/ecosystems/java/` and owns:

- `provider.py`: provider check planning and metadata;
- `classification.py`: Java and Gradle file roles;
- `wrapper.py`: repository-confined wrapper resolution;
- `runner.py`: grouped Gradle execution and policy result composition;
- `reports/`: SpotBugs, Checkstyle, PMD, JaCoCo, and JUnit parsers;
- `findings.py`: normalized finding and fingerprint logic;
- `baseline.py`: deterministic Java finding baseline I/O and comparison;
- `defaults.py`: tested plugin versions, rule ownership, and setup defaults;
- `setup.py`: Java-specific setup plan data, not arbitrary build-file editing.

`JavaProvider` is registered after the TypeScript provider as experimental.
The existing catalog continues to append experimental provider checks after the
stable Python checks. Java classification is active only when Java is enabled.
The ecosystems Tach domain is updated explicitly; no new dependency from core
verification into Java is allowed.

The data flow is:

```text
setup advisor -> Java setup plan -> reviewed Gradle/config edits
                                      |
catalog -> JavaProvider -> grouped Check -> Java runner -> Gradle wrapper
                                                        -> XML reports
                                                        -> normalized findings
                                                        -> baseline comparison
                                                        -> structured JSON artifact
                                                        -> CheckResult
```

## Execution and Configuration Contracts

The complete typed config, wrapper confinement, safe argument policy,
task-to-report expectations, Gradle outcome handling, grouped check planning,
and subprocess-runner protocol are normative in
[Java and Gradle Runtime Contracts](2026-07-15-java-gradle-support-contracts.md).

The central decisions are:

- public config lives under `[tool.agent_maintainer.java]` and maps to one
  frozen `JavaGradleConfig`;
- provider metadata resolves the dotted enablement path `java.enabled` through
  one tested shared helper;
- `gradle_root` is repository-relative, the wrapper lives there, and Gradle's
  working directory is exactly that directory;
- Gradle arguments use a strict allowlist and cannot redirect the build,
  settings, init scripts, included builds, cache roots, or output roots;
- selected tools without tasks are configuration failures, while unselected
  tools are silent;
- every report-producing task has an explicit expectation and Gradle outcome
  policy;
- the Java runner is an internal subprocess whose exit status remains the
  existing command-only `Check` contract, so no executor callback seam is added;
- precommit uses at most one wrapper call and full/CI use at most two.

## Tool Ownership and Defaults

Automatic setup uses all six checks with non-overlapping ownership:

| Tool | Primary responsibility |
| --- | --- |
| Spotless | formatting and import ordering |
| Checkstyle | naming, declarations, API hygiene, structural conventions |
| PMD | design smells, error-prone patterns, performance, complexity |
| SpotBugs | bytecode-level correctness |
| JaCoCo | line and branch coverage |
| Agent Maintainer | file/change budgets, debt comparison, repair facts |

New repositories receive:

- a pinned Spotless Java formatter;
- maximum SpotBugs analysis effort with medium-or-higher confidence;
- a curated Checkstyle ruleset excluding formatting owned by Spotless;
- curated PMD error-prone, best-practice, performance, design, and complexity
  rules;
- cyclomatic complexity 10 per method;
- cognitive complexity 15 per method;
- NPath complexity 200 per method;
- Java file limits of 500 physical and 375 nonblank lines;
- JaCoCo floors of 80% line and 70% branch coverage at bundle level;
- formatting in precommit and all checks in full/CI.

Existing repositories keep their test framework, project layout, and Gradle
conventions. Setup pins tool versions through the existing version catalog,
plugin management, convention plugin, or root plugin block without restructuring
the build.

## Structured Finding Model

Every report adapter produces a canonical finding with:

- tool and rule identifier;
- severity;
- normalized repository-relative path;
- current line range;
- normalized bounded message;
- class, method, or other subject when available;
- numeric measurement when available;
- report origin and module identity.

SpotBugs, Checkstyle, PMD, JaCoCo, and JUnit use XML. Spotless has no standard
machine-readable report, so its exit code and bounded console diff remain
authoritative.

Parsers enforce file-size, element-count, finding-count, and message-size
limits. They reject DTDs, external entities, path escapes, malformed numeric
values, and unsupported schema variants. They produce sanitized facts without
source snippets or absolute checkout paths.

A selected report-backed check that exits zero without a valid required report
fails closed. This matters when an established repository configures
`ignoreFailures` so Agent Maintainer can compare findings with its baseline.

## Ratchet Semantics

### Spotless

New repositories use zero-tolerance `spotlessCheck`. Established repositories
may use Spotless `ratchetFrom` with an explicit base reference, normally the
remote default branch. Setup verifies that the reference is available and
updates shallow CI checkout behavior when necessary. A missing ratchet reference
is a configuration failure, not a request to format the whole repository.

### SpotBugs

New repositories fail on every configured finding. Established repositories
may commit `config/spotbugs/baseline.xml`, generated from a successful XML report
and wired through SpotBugs `baselineFile`. The final report contains new findings
and the Gradle task remains authoritative.

### Checkstyle, PMD, and complexity

These tools do not provide suitable existing-debt baselines. A Java-owned
multiset comparator evaluates their normalized findings against:

```text
.agent-maintainer/java-findings-baseline.json
```

The deterministic, versioned file stores tool identity, normalized signatures,
allowed occurrence counts, numeric ceilings, and the source commit. Line numbers
are not identity because unrelated edits move lines. Repeated identical findings
use multiset counts.

Complexity signatures use path, rule, and class/method subject while storing the
measured value separately. A lower value is an improvement, a higher value is a
regression, an additional occurrence is new debt, and a removed finding becomes
eligible for explicit baseline pruning.

### File size

Java uses the provider-neutral file-baseline assessment and classification, not
the Java finding comparator. New repositories receive the standard limits
immediately. For established repositories, the provider-neutral baseline gains
a versioned per-path ceiling: each oversized file may shrink but not grow. Its
blocking comparator and explicit create/inspect/prune lifecycle are extended
once for every ecosystem rather than reimplemented for Java.

### JaCoCo

Generated Gradle configuration reads configured coverage-property names from
`gradle.properties`, and `jacocoTestCoverageVerification` remains the enforcement
authority. Agent Maintainer compares decimal values with the base branch:
thresholds may stay equal or rise but may not fall. Initial observed values are
rounded down to a whole percentage point. JaCoCo XML supplies actual coverage
and headroom, avoiding the same threshold in two files.

For a single project, the normal report is bundle-level. Multi-project setup
must either configure an explicit aggregate report and verification task or list
per-project report and verification expectations. Agent Maintainer labels and
enforces the selected scope; it never presents project-local coverage as a
repository-wide bundle.

Existing-repository floors are rounded down from successfully observed coverage.
New-repository defaults are 80% line and 70% branch coverage.

### Baseline lifecycle

Verification never modifies baselines. Explicit create, inspect, and prune
operations show proposed changes. Accepting new debt requires an intentional
baseline update. A baseline created from missing, malformed, truncated, or
failed reports is refused.

## Failure Precedence

1. Invalid provider configuration or missing wrapper.
2. Gradle process failure.
3. Missing or malformed required report.
4. New or worsened debt.
5. Advisory improvements and baseline-pruning suggestions.

A report cannot turn a failed Gradle task into a pass. A successful Gradle task
does not override a required external baseline comparison.

## Detection and Classification

`RepoEvidence` gains Java/Gradle facts for wrapper files, settings/build DSLs,
version catalogs, Java source/test counts, and conventional modules. Evidence
collection remains bounded and never invokes Gradle.

The Java classifier assigns:

- `source` to configured production Java roots;
- `test` to configured test Java roots;
- `config` to Gradle scripts, properties, rulesets, and version catalogs;
- `dependency` to wrapper metadata and lock/checksum files;
- `generated` or `ignored` to Gradle output, caches, generated sources, and
  reports;
- `unknown` when custom layout evidence is insufficient.

Classification is conservative. It does not guess that every `.java` file is
production source when it lies outside known or configured roots.

## Setup Workflow

Static setup assessment identifies the Gradle root, DSL, modules, source sets,
existing plugins, version management, reports, CI, and current Agent Maintainer
configuration. It then presents an exact plan.

Automatic mode installs the recommended profile. Advanced mode asks only about
enabled checks, formatter, modules/source sets, coverage, complexity/file limits,
baseline policy, base reference, and CI splitting. Manual mode walks through
every plugin, version, rule, task, report, profile, threshold, suppression, and
baseline destination.

For a newly scaffolded repository, deterministic templates may write the full
known build shape. Existing arbitrary Gradle scripts are not regex-rewritten.
The agent-assisted setup path makes a semantic edit, displays the diff, and
validates it. Deterministic setup refuses ambiguous build structures.

After edits, setup runs:

1. wrapper/version validation;
2. `tasks --all` to confirm exact configured tasks;
3. configured report-producing tasks in observation mode when baselining;
4. baseline generation, if selected;
5. normal doctor;
6. full verification.

Only successful evidence can create a baseline.

## Suppression Policy

Narrow tool-native suppressions are allowed with exact rule identifiers,
smallest practical scope, and human-readable justification. Broad package,
file, repository, `CHECKSTYLE.OFF`, or wildcard suppressions are not defaults.
Existing debt should use a baseline rather than source-wide suppressions.

Java suppression classification is advisory first. New broad suppressions and
suppression growth become provider-aware reviewability facts only after fixture
and real-repository calibration. Generated code is excluded through source-set
and path classification instead of inline suppressions.

## Doctor Contract

Disabled Java support is silent. Enabled support reports:

- wrapper presence, ownership, and executable state;
- Java runtime availability;
- selected checks with missing tasks;
- invalid or duplicate tasks and unsafe arguments;
- unsafe or unmatched report globs;
- missing required baselines;
- unavailable Spotless ratchet references;
- reports never observed after setup;
- setup evidence invalidated by changed Gradle configuration.

Normal doctor does not execute Gradle. An explicit deep probe may run
`gradlew --version` and `tasks --all` with bounded timeouts.

## CI Design

Repository setup proposes two cache-aware jobs:

- static and policy;
- tests and coverage.

They may run in parallel and use the repository's configured JDK toolchain and
Gradle cache convention. Spotless ratcheting requires the configured base
reference to be fetched. Setup modifies an existing workflow only after showing
the diff and does not replace the repository's CI framework.

In Agent Maintainer's own CI:

- hermetic parser, planner, config, and fake-wrapper tests remain in normal
  Python jobs;
- a separate cached live-Gradle fixture job runs when Java-provider paths,
  templates, or fixtures change;
- broader wrapper/JDK coverage may run nightly while the provider is
  experimental;
- the live job becomes a required release gate before provider promotion.

## Validation and Delivery

The detailed test matrix, phased delivery order, documentation changes,
performance gates, and provider-promotion criteria are maintained in the
[Java and Gradle Validation and Rollout](2026-07-15-java-gradle-support-validation.md)
companion. Those gates are normative for implementation.

## Success Criteria

The design succeeds when an agent can take a new or established Gradle Java
repository through reviewed setup, run fast grouped verification through the
checked-in wrapper, receive structured actionable failures, and improve quality
without either accepting historical debt repeatedly or hiding it behind broad
suppressions. The implementation must achieve that without weakening Python,
adding a public plugin API, or turning Agent Maintainer into a build system.
