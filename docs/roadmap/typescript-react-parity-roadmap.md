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
- TypeScript/React doctor and setup-advisor guidance.

Still missing before a promotion assessment:

- Blocking TypeScript/React reviewability gates.
- Advisory package-manager and workspace detection.
- First-class dead-code, dependency, security, architecture, changed-line
  coverage, mutation, and generated-file adapters.
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
| pip-audit | OSV Scanner plus package-manager audit | Strong replacement | Add lockfile-aware OSV facts before package-manager audit summaries. |
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

1. Phase 178: advisory package-manager and workspace detection.
2. Knip unused-code and dependency facts.
3. OSV and package-manager audit facts.
4. Dependency-cruiser architecture-boundary facts, followed by declared Nx
   boundary support.
5. LCOV changed-line coverage facts.
6. React hooks, JSX accessibility, and Testing Library recommendations.
7. Explicit generated-file and framework policy evidence.
8. StrykerJS mutation facts with a runtime-cost guard.
9. TypeScript/React blocking-gate promotion assessment.

Only Phase 178 is numbered in advance. Assign later phase numbers when each
slice has an approved design and implementation plan.

## Phase 178 Safety Boundary

Phase 178 may observe root `package.json` metadata, the `packageManager` field,
Corepack-related declarations, npm/pnpm/Yarn/Bun lockfiles, workspace manifests,
script names, and explicit Agent Maintainer workspace configuration.

Facts retain file-and-field provenance. Malformed metadata, multiple lockfiles,
conflicting declarations, and unsupported workspace shapes remain visible as
bounded advisory ambiguity. Agent Maintainer does not select a preferred package
manager, fall back to npm, or infer nested package ownership.

Doctor and setup-advisor may explain the evidence and show reviewed
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
