# TypeScript/React Parity Roadmap

This roadmap defines the evidence needed for the experimental
TypeScript/JavaScript provider to approach Python-provider parity in TypeScript
and React repositories. TypeScript stays advisory until each blocking candidate
has low-noise fixture and external-repository evidence.

## Integration Strategy

Land each bounded capability through focused pull requests to `main`. Do not
use a long-lived integration branch: experimental provider status and explicit
configuration already isolate incomplete TypeScript behavior while preserving
normal review, rollback, and CI on every slice.

The stale `origin/codex/react-typescript-parity-roadmap` branch is historical
reference only. Phase 176 remains Codex terminal-rewake hardening; this roadmap
is Phase 177.

## Current State

Already landed:

- React-shaped TSX and workspace reviewability evidence.
- Explicit root and workspace-owned lint, typecheck, and test commands.
- TypeScript compiler, ESLint JSON, Jest/Vitest JSON, Istanbul summary, and LCOV
  repair facts.
- Ecosystem-neutral OSV Scanner v2 facts with grouped aliases and safe lockfile
  provenance.
- Explicit dependency-cruiser architecture commands with bounded, path-safe
  cruise-result facts and summaries.
- Advisory LCOV changed-line coverage for existing root or workspace artifacts,
  with weighted executable-line facts and no threshold gate.
- TypeScript/React doctor and setup-advisor guidance.
- Advisory package-manager and workspace detection with file-and-field
  provenance.

Still missing before a promotion assessment:

- Blocking TypeScript/React reviewability gates.
- First-class package-manager audit, mutation, generated-file, and broader
  security adapters.
- Broader external evidence across React, Vite, Next.js, and workspace layouts.

## Parity Tool Map

| Python capability | TypeScript/React candidate | Status | Decision |
|---|---|---|---|
| Black/Ruff formatting | Biome format or Prettier | Strong replacement | Recommend a detected project formatter; never add one automatically. |
| Ruff/Pylint/Wemake lint | ESLint, typescript-eslint, React plugins, SonarJS | Partial replacement | Measure typed ESLint and React rulepacks instead of imitating one Python tool. |
| MyPy/Pyright | `tsc --noEmit` or project typecheck scripts | Strong replacement | Preserve explicit command ownership and stable compiler facts. |
| Pytest/unittest | Vitest, Jest, Playwright component tests, Testing Library | Strong replacement | Execute configured scripts only and parse stable artifacts. |
| Coverage.py/diff-cover | Istanbul/V8 LCOV plus a changed-line adapter | Partial replacement | Build advisory LCOV changed-line facts before any threshold gate. |
| Tach/import-linter | dependency-cruiser, Nx boundaries, ESLint boundaries | Partial replacement | Start with dependency-cruiser; support Nx only when a repository declares it. |
| Vulture/Deptry | Knip | Strong replacement | Parse stable Knip JSON for unused files, exports, dependencies, and unresolved binaries. |
| pip-audit | OSV Scanner plus package-manager audit | Strong replacement | Lockfile-aware OSV facts are complete; add package-manager audit summaries next. |
| Bandit | Semgrep JS/TS rules and ESLint security plugins | Partial replacement | Keep advisory until external evidence measures false positives. |
| Gitleaks | Gitleaks | Ecosystem-neutral | Reuse the existing secret scan without a TypeScript adapter. |
| Radon/Xenon | ESLint complexity and SonarJS cognitive complexity | Partial replacement | Measure advisory facts before defining thresholds. |
| Mutmut | StrykerJS | Strong replacement | Add report parsing and a runtime-cost guard before ratcheting. |
| Python SBOM | CycloneDX npm or package-manager SBOM output | Strong replacement | Detect optional artifacts before requiring execution. |
| License reporting | SBOM license fields | Partial replacement | Prefer existing SBOM data over another command surface. |
| Interrogate | TypeDoc or API Extractor for libraries | No app-repo equivalent | Do not force Python docstring coverage onto React applications. |
| DocSync | DocSync | Ecosystem-neutral | Keep the existing language-agnostic documentation contract. |
| React hooks | `eslint-plugin-react-hooks` | Strong React signal | Recommend when present or explicitly selected. |
| JSX accessibility | `eslint-plugin-jsx-a11y` | Strong React signal | Start advisory and measure external-repository noise. |
| Testing Library quality | `eslint-plugin-testing-library` | Strong React signal | Recommend only for repositories that use Testing Library or opt in. |
| Generated-file policy | Explicit classifier and framework evidence | No single replacement | Cover framework and codegen outputs with fixture-backed rules. |

## Implementation Sequence

1. Phase 178: advisory package-manager and workspace detection is complete.
2. Phase 179: Knip unused-code and dependency facts are complete.
3. Phase 180: OSV dependency facts are complete.
4. Phase 181: dependency-cruiser architecture-boundary facts are complete.
5. Phase 182: advisory LCOV changed-line coverage facts are complete.
6. Package-manager audit facts are the next parity slice.
7. Explicit generated-file and framework policy evidence.
8. TypeScript/React blocking-gate promotion assessment.
9. Declared Nx boundary support.
10. React hooks, JSX accessibility, and Testing Library recommendations.
11. StrykerJS mutation facts with a runtime-cost guard.

Assign later phase numbers when each slice has an approved design and
implementation plan.

## Phase 182 LCOV Changed-Line Coverage Boundary

Phase 182 adds `test-intel typescript-coverage`, which reads an existing LCOV
artifact and intersects its executable `DA` lines with a selected Git diff.
Relative LCOV sources resolve beneath an explicit source root; absolute sources
are accepted only inside the repository. Missing files remain visible but do
not become synthetic uncovered lines. Aggregate coverage is weighted across
all executable changed lines rather than averaging per-file percentages.

The command does not run a test tool, infer a package manager, call
`diff-cover`, or configure a threshold, ratchet, verifier profile, or blocking
gate. Pinned committed LCOV projections from npm/TypeScript/Jest V8
`CMSgov/qpp-measures-data` and pnpm-workspace `starbeamjs/starbeam` provide
offline public compatibility evidence. TypeScript/JavaScript remains
experimental.

## Phase 181 Dependency-Cruiser Boundary

Phase 181 runs only explicit root or workspace
`typescript_dependency_cruiser_command` arrays. Root
`typescript_dependency_cruiser_profiles` defaults to `full` and `ci`. Agent
Maintainer does not infer a package manager, add JSON reporter flags, install
dependency-cruiser, generate configuration, invent rules, or reinterpret exit
status.

The shared parser reads only `summary.violations`, sorts before retaining 500
normalized findings, and bounds failed-check summaries to 50 total lines.
Unsafe sources are display-only and never become context targets. Pinned npm
`decentralized-identity/dwn-sdk-js` and pnpm-workspace
`hicommonwealth/commonwealth` projections provide offline public compatibility
evidence. dependency-cruiser is the
TypeScript/JavaScript architecture-boundary counterpart to Tach for this
provider; Python Tach, Archguard, and declared Nx policies remain separate.
TypeScript/JavaScript remains experimental.

## Phase 180 OSV Boundary

Phase 180 reuses the existing global `osv-scanner` check. It does not add a
TypeScript command, infer a package manager, or enable the manual gate by
default. The shared OSV Scanner v2 parser emits one finding per alias group,
retains fixed versions only from OSV range events, and sorts findings before a
500-finding parser bound. Compact summaries use at most 50 total lines, while
context packs retain the existing five facts per failed check.

Valid repository-relative lockfile paths remain available as provenance.
Absolute paths, parent traversal, and Windows drive paths are reduced to a safe
filename label and never become a context target. Synthetic fixtures establish
malformed-neighbor and path-rejection behavior. Bounded projections from pinned
`vitest-dev/eslint-plugin-vitest` and
`jsynowiec/node-typescript-boilerplate` revisions record pnpm and npm
compatibility without making tests depend on the network or scanner binary.
TypeScript/JavaScript remains experimental.

## Phase 179 Knip Boundary

Phase 179 runs only explicit root or workspace `typescript_knip_command` arrays
and uses root `typescript_knip_profiles`, which defaults to `full` and `ci`.
Agent Maintainer does not infer commands, append reporter flags, enforce a Knip
version, add thresholds, or change the configured process exit status.

The JSON parser normalizes supported unused-code, dependency, binary, and
unresolved findings. It sorts before retaining 500 facts and bounds compact
summaries to 50 total lines. Synthetic fixtures define the category contract;
pinned TanStack Query and Astro captures provide public compatibility evidence.
TypeScript/JavaScript remains experimental.

## Phase 178 Safety Boundary

Phase 178 observes root `package.json` metadata, the `packageManager` field,
Corepack-related declarations, npm/pnpm/Yarn/Bun lockfiles, workspace manifests,
script names, and explicit Agent Maintainer workspace configuration.

Facts retain file-and-field provenance. Malformed metadata, multiple lockfiles,
conflicting declarations, and unsupported workspace shapes remain visible as
bounded advisory ambiguity. Agent Maintainer does not select a preferred package
manager, fall back to npm, or infer nested package ownership.

Setup advisor explains the evidence and shows reviewed
configuration choices. The provider executor continues to use only explicit
root or workspace command arrays. Repository evidence must never become
subprocess arguments.

## Evidence And Promotion Criteria

Every future blocking candidate requires temporary-Git fixture coverage and at
least two external real-repository comparisons. Evidence must measure noise,
repair usefulness, runtime cost where relevant, and behavior across React,
Vite, Next.js, and workspace layouts.

TypeScript/React can move beyond experimental only when:

- blocking candidates have explicit low-noise evidence;
- doctor and setup-advisor remain explicit-command first;
- changed-line coverage and repair facts are stable;
- unsupported package managers, runners, frameworks, generated files, and
  monorepo layouts are documented;
- Python-provider behavior and architecture ownership do not regress;
- the complete focused, broad local, and hosted CI gates pass.

## Out Of Scope

- Executing inferred package scripts or package-manager commands.
- Enabling TypeScript/React blocking gates by default before promotion.
- Adding another ecosystem before the TypeScript/React promotion assessment.
- Weakening Python behavior to create a superficially provider-neutral API.
- Forcing Python-only documentation rules onto React application code.
