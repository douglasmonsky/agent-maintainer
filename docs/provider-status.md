<!-- docsync:object docs.provider_status.overview -->
# Ecosystem Provider Status

Agent Maintainer is Python-core today, with an internal provider seam for
careful expansion. Experimental providers are not feature parity.

The built-in experimental TypeScript/JavaScript, Java/Gradle, and C/C++ (CMake)
providers are behind explicit configuration.

## Current Providers

| Ecosystem | Maturity | Current Support | Not Yet |
|---|---|---|---|
| Python | Core/reference | Full check catalog, reviewability policies, coverage, diff coverage, mutation ratchets, security and dependency checks, doctor support, repair facts, and starter templates. | External plugin API. |
| TypeScript/JavaScript | Experimental | Explicit configured lint/typecheck/test/Knip/dependency-cruiser/package-manager-audit commands; file classification; advisory suppression classification; `tsc --pretty false`, ESLint JSON, Jest/Vitest JSON, Istanbul/LCOV, bounded Knip, dependency-cruiser, and package-manager audit repair facts, grouped OSV dependency facts through the ecosystem-neutral manual gate, and advisory LCOV changed-line coverage for existing artifacts; format-aware doctor setup and repair-fact output guidance rows. Advisory package-manager and workspace evidence. | Starter files, coverage command/gate adapters, mutation testing, broader security adapters, declared Nx boundaries, and blocking reviewability gates. |
| Java/Gradle | Experimental calibrated ratchets | Explicit checked-wrapper task groups; reviewed setup; Spotless/native SpotBugs ratchets; exact upward-only JaCoCo thresholds; truthful project coverage; bounded XML evidence; Java debt baselines; exact repair facts; live Linux/Windows Gradle fixtures; static doctor checks. | Maven, automatic aggregate coverage, broad Java-specific blocking reviewability, production-scale calibration, and stable-provider guarantees. |
| C/C++ (CMake) | Experimental foundation | Classification, config, suppression evidence, and static doctor only. All evidence is advisory-only. | Command execution and typed reports until Phase 188; report parsing, sanitizers, blocking policy, promotion, non-CMake build systems, and a stable external provider API. |

There is no active Go provider on `main`. Go remains archived historical work
until active experimental providers have stronger evidence and the provider
seam has settled.

## Current Focus

TypeScript/JavaScript is again the active parity track. TypeScript/React parity
work now advances through focused pull requests to `main`. The
[TypeScript/React Parity Roadmap](roadmap/typescript-react-parity-roadmap.md)
keeps the provider experimental while evidence accumulates.

Phase 178 package-manager and workspace evidence is advisory only. The setup
assessment JSON preserves file-and-field provenance for recognized declarations,
lockfiles, and workspace manifests, but never selects a manager, expands workspace globs,
or creates a command. Phase 179 Knip unused-code and dependency facts are
complete. Synthetic category coverage includes pinned TanStack Query and Astro
comparisons. Phase 180 OSV dependency facts are complete. The existing global
manual gate now yields bounded alias-grouped facts with safe lockfile
provenance, backed by pinned npm and pnpm projections. Phase 181
dependency-cruiser architecture facts are complete. Phase 182 advisory LCOV
changed-line coverage facts are also complete.
Pinned `decentralized-identity/dwn-sdk-js` and
`hicommonwealth/commonwealth` projections cover npm and pnpm-workspace
cruise-result shapes. Pinned committed LCOV projections from
`CMSgov/qpp-measures-data` and `starbeamjs/starbeam` cover npm/TypeScript/Jest
V8 and pnpm-workspace shapes. Phase 192 package-manager audit facts are now
complete: explicit manager and command ownership, bounded normalized advisory
facts, and offline pinned npm/pnpm projections. Yarn and Bun remain fixture-only
until equivalent public evidence is collected; TypeScript/JavaScript remains
experimental.

Java/Gradle remains the second built-in experimental priority. Neither provider
is promoted by this sequencing decision. TypeScript still must satisfy the bar
in
[TypeScript Provider Maturation Notes](case-studies/typescript-provider-maturation.md).
Java's current contract is in the
[Experimental Java/Gradle Provider](java-gradle-provider.md), with measured
controlled evidence in the
[Java/Gradle Provider Calibration](case-studies/java-gradle-provider-calibration.md).

## Java/Gradle Setup, Native Ratchets, And Structured Evidence

The provider runs only explicit tasks already owned by the repository:

```toml
[tool.agent_maintainer.java]
enabled = true
gradle_root = "."
checks = ["spotless", "spotbugs", "checkstyle", "pmd", "test", "jacoco"]
spotless_tasks = ["spotlessCheck"]
spotbugs_tasks = ["spotbugsMain", "spotbugsTest"]
checkstyle_tasks = ["checkstyleMain", "checkstyleTest"]
pmd_tasks = ["pmdMain", "pmdTest"]
test_tasks = ["test"]
jacoco_report_tasks = ["jacocoTestReport"]
jacoco_verify_tasks = ["jacocoTestCoverageVerification"]
projects = [":"]
jacoco_ratchet_ref = "origin/main"

# Established repositories may enable these after reviewed setup evidence.
spotless_ratchet_ref = "origin/main"
spotbugs_baseline = "config/spotbugs/baseline.xml"
findings_baseline = ".agent-maintainer/java-findings-baseline.json"
```

The checked-in wrapper at `gradle_root` is mandatory; Agent Maintainer never
falls back to a system Gradle. Recognized scaffolds use deterministic Groovy or
Kotlin DSL fragments and bundled rulesets. An arbitrary existing build requires
a typed semantic-edit handoff, a displayed diff, validation evidence, and the
same reviewed digest before apply; setup never performs a regex rewrite.

Spotless `ratchetFrom` requires an explicit available Git reference and never
fetches or falls back to formatting the whole repository. A native SpotBugs
`FindBugsFilter` may be created only from successful, complete, fresh report
evidence, and normal verification never creates or mutates that baseline.
Normal doctor remains static and never executes Gradle. It checks the configured
Git reference and securely parses the repository-confined baseline file without
running the wrapper. Setup-only `tasks --all` requires a displayed approval.

Reviewed GitHub Actions plans preserve the chosen JDK convention, add separate
cached `static-and-policy` and `tests-and-coverage` jobs, and refuse to overwrite
an existing managed workflow or an unknown CI framework.
The repository's live fixture workflow is configured to validate Groovy and
Kotlin DSL checked wrappers on Linux and Windows. It runs both grouped Agent
Maintainer checks, native Spotless/SpotBugs ratchets, Checkstyle, PMD, tests,
JaCoCo, and bounded report parsing without lengthening protected aggregate
verification.

Successful Gradle executions validate bounded Checkstyle, PMD, SpotBugs, JUnit,
and JaCoCo XML evidence against exact task outcomes, configured report paths,
freshness, and parser limits. The runner publishes only sanitized bounded facts
and never persists raw Gradle XML. Java exact repair facts consume that one
runner artifact and never reopen report paths.

The Java findings baseline lifecycle is explicit through
`assess java-baseline create|inspect|prune`. Create and prune require a clean
worktree plus a complete, non-truncated static runner artifact produced at the
current Git commit; verification never mutates the baseline. Checkstyle, PMD,
and normalized SpotBugs findings use multiset counts, while numeric complexity
measurements use per-occurrence ceilings. Provider-neutral file ceilings remain
a separate baseline and command surface. Exact JaCoCo floors are read from
`gradle.properties`, compared upward-only against an explicit base reference,
and reported separately for every real project or aggregate coverage scope.
The complete nested key inventory and environment overrides are in the
[configuration reference](configuration-reference.md).

DocSync is not an ecosystem provider. It is a repository documentation
traceability gate that Agent Maintainer detects when `.docsync/trace.yml`
exists and runs in local verification profiles.

## Design Rule

Core owns the verification loop: profiles, command execution, bounded logs,
run-scoped diagnostics, reports, context packs, repair plans, and hooks.

Providers own ecosystem-specific excellence: commands, file classification,
suppression rules, coverage artifacts, doctor rows, repair facts, scaffold
snippets, and maturity-specific guidance.

If a provider abstraction makes an existing Python feature harder to express,
the abstraction is wrong. Python remains the reference provider and may stay
richer than experimental providers.

## Reviewability Policy

Current reviewability gates are globally scheduled but Python-backed.
Experimental TypeScript/JavaScript and Java/Gradle do not yet receive complete
blocking change-budget, suppression-budget, file-length, structure-cohesion, or
test-relevance policy gates.

TypeScript/JavaScript changed files are advisory, but blocking reviewability
policy is not fully multi-ecosystem yet.

In the current beta:

- Python remains the core/reference provider with full reviewability policy.
- TypeScript/JavaScript is the first serious non-Python maturation target.
- TypeScript/JavaScript providers run explicitly configured commands.
- TypeScript/JavaScript emits advisory changed-file and suppression facts
  through `assess reviewability`.
- TypeScript/JavaScript does not yet receive blocking change-budget,
  suppression-budget, file-length, structure-cohesion, or test-relevance gates.
- Java/Gradle contributes explicit grouped verification, provider
  classification, reviewed setup, native Spotless/SpotBugs ratchets, structured
  report evidence, exact repair facts, and blocking provider-neutral per-path
  file ceilings, exact upward-only JaCoCo thresholds, truthful coverage
  topology, live cross-platform fixtures, and controlled calibration evidence.
  Broader Java-specific change-budget, suppression, cohesion, test-relevance,
  mutation, dependency, and security gates remain deferred.
<!-- docsync:object.end docs.provider_status.overview -->
