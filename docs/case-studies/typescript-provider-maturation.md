<!-- docsync:object docs.typescript_maturation.overview -->
# TypeScript Provider Maturation Notes

These notes track how TypeScript/JavaScript becomes the first serious
non-Python provider maturation target. The goal is to learn what should become
shared provider infrastructure without forcing Node-specific assumptions into
core.

## Current Posture

- Python remains the core/reference provider.
- TypeScript/JavaScript is the first non-Python provider to mature beyond thin
  command execution.
- No TypeScript/JavaScript reviewability signal is blocking yet.

## Fixture Evidence

Phase 100 added TypeScript reviewability fixtures for:

- source-plus-test changes that should stay low-noise;
- source-only heavy changes that should produce advisory findings;
- generated build output paths that should not inflate source/test signals;
- dependency files such as `package-lock.json` and `pnpm-lock.yaml`;
- config files such as `vite.config.ts` and `next.config.js`;
- broad and narrow suppressions.

The fixtures intentionally exercise `assess reviewability` rather than the
standalone classifier. That proves users and agents see useful advisory output
without changing blocking verifier behavior.

## Real-Repo Diff Evidence

Phase 131 added temporary Git repository tests that run the public
`assess reviewability --json` command against TypeScript diffs. The evidence
covers:

- source-plus-test changes producing TypeScript provider summaries without
  advisory source-without-test findings;
- source-heavy source-only changes producing TypeScript `source-heavy` and
  `source-without-test` advisory findings;
- broad TypeScript suppression counting through the public JSON payload.

This closes one maturation gap between patched fixture readers and real Git
diff behavior. It still does not justify blocking TypeScript reviewability
gates.

Phase 138 added additional temporary Git repository shapes for npm, pnpm, Vite,
and Vitest. These tests prove npm/Vite/Vitest source-plus-test changes stay
low-noise, and pnpm config/lockfile changes report config and dependency roles
without source-heavy or source-without-test findings. At least one external
real-repo comparison is still needed before any promotion beyond advisory
output. Phase 165 added a React app-shaped temporary Git repository fixture
covering React dependencies, TSX source, TSX tests, and a React entrypoint
while staying advisory-clean. Phase 166 added pnpm workspace-shaped evidence
for root package metadata, workspace metadata, lockfile metadata, package
metadata, workspace TSX source, and workspace TSX tests. Phase 167 added
structured `typescript-test` repair-fact coverage for React/Vite/Next-adjacent
outputs: Vitest task-style JSON, Istanbul `coverage-summary.json`, and LCOV
`lcov.info` artifacts. This improves failed-check repair context when
repositories already produce stable artifacts; it does not add TypeScript
coverage enforcement or default framework commands. Broader external framework
samples remain needed before promotion beyond advisory output.

Phase 139 added one external public-repository comparison against
`vitest-dev/eslint-plugin-vitest` commit
`7c697f8a53d7d7551b00ef11217d58cd45a0cf7d`, compared with its parent
`8fff9690c0c4008f93a636a62425dbe520ec7ce7`. The public reviewability command
classified one TypeScript source file and one TypeScript test file, reported
zero unclassified files, and produced zero advisory findings. This is useful
signal, not a promotion by itself: broader repository samples are still needed
before TypeScript reviewability becomes blocking or supported.

Phase 140 added a second external comparison from
`jsynowiec/node-typescript-boilerplate` commit
`550dfd2a976d69254ed71eb6f5a6c5ee20060807`, a Jest-to-Vitest migration. The
reviewability output stayed advisory-clean while classifying TypeScript source,
test, and dependency changes plus global config and docs changes. This broadens
evidence beyond one lint-plugin repository, but TypeScript remains experimental
until more framework and workspace shapes are sampled.

## Advisory Threshold Evidence

Current fixture evidence supports considering advisory thresholds for:

- source-only TypeScript changes;
- source-heavy TypeScript changes by changed source files and changed source
  lines;
- broad TypeScript/JavaScript suppressions.

Current fixture evidence does not yet support blocking thresholds. It also does
not yet support package-manager autodetection, test-runner-specific defaults, or
framework-specific generated-file policy beyond the existing classifier.

Phase 136 made advisory threshold names active config fields for
`assess reviewability`. They stay TypeScript-owned and non-blocking until
real-repo output proves low noise:

```toml
[tool.agent_maintainer]
typescript_advisory_source_warn_files = 4
typescript_advisory_source_warn_lines = 200
typescript_advisory_broad_suppression_warn = 1
```

These fields tune advisory findings only. They do not change verifier exit
status, Python reviewability gates, or TypeScript provider maturity.

## Lessons To Capture

Use this page as an implementation notebook while TypeScript matures. Track:

- which repository shapes stay low-noise;
- where package-manager assumptions stay provider-specific;
- which output formats are stable enough for exact repair facts, including test
  and coverage artifacts;
- whether suppressions should remain advisory;
- which advisory threshold values stay low-noise across real repositories;
- which signals are too framework-specific for defaults;
- whether any abstraction makes Python less capable.

## Promotion Bar

TypeScript/JavaScript should not move toward supported status until it has:

- fixture and temporary-Git evidence for common npm, pnpm, Vite, and Vitest
  project shapes;
- at least one external real-repo comparison pass with acceptable noise;
- broader external comparisons across more framework and workspace shapes;
- stable explicit-command behavior;
- workspace command ownership semantics before recursive package discovery;
- clear doctor messages for missing commands and executables;
- structured repair facts only for stable test and coverage outputs;
- documented unsupported package managers, runners, and frameworks;
- no blocking gates enabled by default.

Blocking reviewability policy is a later opt-in step. It is not part of this
maturation note.
<!-- docsync:object.end docs.typescript_maturation.overview -->
