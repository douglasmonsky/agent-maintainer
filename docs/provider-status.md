<!-- docsync:object docs.provider_status.overview -->
# Ecosystem Provider Status

Agent Maintainer is Python-core today, with an internal provider seam for
careful expansion. Experimental providers are not feature parity.

The built-in experimental TypeScript/JavaScript and Java/Gradle providers are
behind explicit configuration.

## Current Providers

| Ecosystem | Maturity | Current Support | Not Yet |
|---|---|---|---|
| Python | Core/reference | Full check catalog, reviewability policies, coverage, diff coverage, mutation ratchets, security and dependency checks, doctor support, repair facts, and starter templates. | External plugin API. |
| TypeScript/JavaScript | Experimental | Explicit configured lint/typecheck/test commands; file classification; advisory suppression classification; `tsc --pretty false`, ESLint JSON, Jest/Vitest JSON, and Istanbul/LCOV repair facts; format-aware doctor setup and repair-fact output guidance rows. | Package-manager autodetection, starter files, coverage adapters, mutation testing, dependency/security adapters, and blocking reviewability gates. |
| Java/Gradle | Experimental setup/native ratchets | Explicit checked-wrapper task groups; classification; reviewed setup for recognized and arbitrary builds; bounded task and SpotBugs report evidence; Spotless and native SpotBugs ratchets; static doctor checks; reviewed parallel CI plans. | Cross-tool structured findings baselines, repair facts, provider-neutral file ceilings, JaCoCo threshold ratchets, live CI fixtures, and calibration evidence. |

There is no active Go provider on `main`. Go remains archived historical work
until active experimental providers have stronger evidence and the provider
seam has settled.

## Current Focus

TypeScript/JavaScript remains the first maturation evidence track. Java/Gradle
is now the second built-in experimental priority for the maintainer's future
repositories; that priority intentionally supersedes the former
TypeScript-before-any-other-provider sequence without promoting either provider.
TypeScript still must satisfy the bar in
[TypeScript Provider Maturation Notes](case-studies/typescript-provider-maturation.md).

## Java/Gradle Setup And Native Ratchets

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

# Established repositories may enable these after reviewed setup evidence.
spotless_ratchet_ref = "origin/main"
spotbugs_baseline = "config/spotbugs/baseline.xml"
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
an existing managed workflow or an unknown CI framework. Checkstyle and PMD
findings baselines remain deferred. Structured repair facts and JaCoCo threshold
ratchets remain deferred as well. The complete nested key inventory and sole
environment override are in the
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
  classification, reviewed setup, and native Spotless/SpotBugs ratchets; its
  broader structured reviewability ratchets remain deferred.
<!-- docsync:object.end docs.provider_status.overview -->
