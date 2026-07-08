# TypeScript/React Parity Roadmap

This roadmap defines the work needed for the TypeScript/JavaScript provider to
approach Python-provider parity for TypeScript and React repositories. The
track starts from the current explicit-command provider and keeps TypeScript
advisory-only until each signal has low-noise fixture and real-repository
evidence.

## Branch Strategy

Build this track on `codex/react-typescript-parity-roadmap`, not directly on
`main`. Implementation PRs for this track should target the integration branch
while parity work is still incomplete. Merge the integration branch back to
`main` only after the promotion criteria below are satisfied and broad local
plus GitHub CI checks pass.

## Current State

Already landed:

- React-shaped TSX reviewability fixtures and public command coverage.
- Package-manager and workspace evidence for npm, pnpm, Vite, and Vitest
  repository shapes.
- Structured TypeScript, ESLint JSON, Jest-compatible JSON, Vitest task-style
  JSON, Istanbul `coverage-summary.json`, and LCOV repair facts.
- TypeScript/React doctor and setup-advisor guidance for explicit commands.
- Workspace-owned TypeScript command configuration and setup examples.

Still missing before parity:

- Blocking TypeScript/React reviewability gates.
- Package-manager and workspace detection that is advisory before it executes
  anything.
- First-class adapters for dead code, dependency integrity, dependency
  security, architecture boundaries, diff coverage, mutation testing, and
  generated-file policy.
- More external real-repository evidence across React, Next.js, Vite, and
  workspace layouts.

## Parity Tool Map

| Python capability | TypeScript/React candidate | Parity status | Roadmap decision |
|---|---|---|---|
| Black/Ruff formatting | Biome format or Prettier | Strong replacement | Recommend detected project formatter first; do not add a new formatter by default. |
| Ruff/Pylint/Wemake-style lint | ESLint with `typescript-eslint`, React plugins, SonarJS, and project rules | Partial replacement | Start with typed ESLint and React rulepack evidence. Treat Wemake-style strictness as policy composition, not one tool. |
| MyPy/Pyright type checking | `tsc --noEmit` and project typecheck scripts | Strong replacement | Keep explicit command execution; add better setup detection and repair facts before default recommendations. |
| Pytest/unittest | Vitest, Jest, Playwright component tests, Testing Library | Strong replacement | Prefer configured test scripts; parse stable JSON artifacts only. |
| Coverage.py/diff-cover | Vitest V8/Istanbul, Jest Istanbul, LCOV, custom changed-line adapter | Partial replacement | Build LCOV changed-line adapter before any blocking coverage gate. |
| Tach/import-linter architecture | dependency-cruiser, Nx module boundaries, `eslint-plugin-boundaries`, Madge | Partial replacement | Start with dependency-cruiser evidence, then add Nx policy support only for repos that already use Nx. |
| Vulture dead code | Knip | Strong replacement | Add Knip adapter and facts before any warning can block. |
| Deptry dependency hygiene | Knip with depcheck fallback | Partial replacement | Prefer Knip because it covers unused exports, files, and dependencies in TS/JS projects. |
| pip-audit | OSV Scanner plus package-manager audit | Strong replacement | Add OSV lockfile adapter first, then advisory npm/pnpm/yarn/bun audit summaries. |
| Bandit security lint | Semgrep JS/TS rules plus ESLint security plugins | Partial replacement | Keep security lint advisory until false-positive evidence is measured. |
| Gitleaks secrets | Gitleaks | Already ecosystem-neutral | Reuse existing secret scanning; no TypeScript-specific tool needed. |
| Radon/Xenon complexity | ESLint complexity rules plus SonarJS cognitive complexity | Partial replacement | Add advisory metrics, not blocking thresholds, until fixture noise is measured. |
| Mutmut mutation testing | StrykerJS | Strong replacement | Add StrykerJS artifact parsing and mutation score ratchet only after runtime cost is measured. |
| SBOM generation | CycloneDX npm or native package-manager SBOM output | Strong replacement | Add optional artifact detection before requiring command execution. |
| License reporting | SBOM license fields or license-checker variants | Partial replacement | Prefer SBOM-derived evidence to avoid another command surface. |
| Interrogate docstring coverage | No known app-repo replacement | No known replacement | Do not force Python public-API docstring rules onto React app code. Consider API Extractor/TypeDoc only for library packages. |
| DocSync public-doc evidence | No known direct replacement | No known replacement | Keep DocSync language-agnostic; do not invent a TypeScript substitute. |
| React hooks correctness | `eslint-plugin-react-hooks` | Strong React-specific signal | Add React rulepack recommendation and evidence. |
| JSX accessibility | `eslint-plugin-jsx-a11y` | Strong React-specific signal | Add advisory recommendation first, then real-repo noise review. |
| Testing Library quality | `eslint-plugin-testing-library` | Strong React-specific signal | Recommend only for projects that already use Testing Library or opt in. |
| Generated-file policy | Custom classifier plus framework evidence | No single replacement | Build explicit generated path policy for Next.js, Vite, codegen, route manifests, and coverage/build outputs. |

## Implementation Slices

1. Package-manager and workspace detection hardening.
   Detect `packageManager`, lockfiles, workspace manifests, Corepack usage, and
   package scripts. Output advisory setup facts only. Do not infer or execute
   commands from detection.

2. Knip unused-code and dependency adapter.
   Add parser support for stable Knip JSON, repair facts for unused files,
   exports, dependencies, and unresolved binaries, plus fixture evidence for
   React/Vite/Next packages.

3. OSV and package-manager audit adapter.
   Add lockfile-aware OSV Scanner output parsing, bounded vulnerability facts,
   and optional package-manager audit summaries. Keep severity thresholds
   advisory until false-positive policy is clear.

4. Dependency boundary adapter.
   Add dependency-cruiser JSON parsing for architecture violations. Follow with
   Nx boundary support only when a repository already declares Nx boundaries.

5. LCOV changed-line coverage adapter.
   Map LCOV records to changed lines and produce file/line facts comparable to
   Python diff coverage. Keep blocking disabled until React fixture and external
   samples show low noise.

6. React lint rulepack recommendations.
   Teach doctor/setup-advisor to recognize React hooks, JSX accessibility, and
   Testing Library lint coverage without adding dependencies or changing
   project config.

7. Generated-file and framework policy.
   Extend classifier evidence for Next.js, Vite, React Router, Storybook, code
   generation, build outputs, coverage outputs, and route manifests. Keep policy
   explicit and test fixture-backed.

8. StrykerJS mutation adapter.
   Parse mutation reports, capture score and survivor facts, and add a cost
   guard. Do not make mutation blocking until runtime and survivor quality are
   measured.

9. TypeScript/React blocking-gate promotion assessment.
   Review fixture plus external-repository data, set any opt-in thresholds,
   document unsupported surfaces, and decide whether any TypeScript/React signal
   can graduate from advisory to blocking.

## Promotion Criteria

TypeScript/React can move beyond experimental only when:

- Every blocking candidate has temporary-Git fixture evidence and at least two
  external real-repository comparisons.
- No candidate signal worsens Python-provider behavior or Tach ownership.
- Doctor and setup-advisor messages remain explicit-command first.
- Unsupported package managers, test runners, framework defaults, generated
  files, and monorepo layouts are documented.
- CI profile behavior, changed-code coverage, and repair-fact output are stable.
- The integration branch has passed focused adapter tests, `tach check --exact`,
  DocSync checks where docs changed, diff hygiene, and a broad verifier profile.

## Out Of Scope

- Arbitrary package script inference that executes commands without explicit
  config.
- Enabling TypeScript/React blocking gates by default before promotion.
- Adding a new ecosystem before TypeScript/React parity is assessed.
- Replacing working Python-provider checks with provider-neutral abstractions
  that make the Python path weaker.
