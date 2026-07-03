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

Phase 131 added temporary Git repository tests that run public
`assess reviewability --json` against actual TypeScript diffs. This evidence
covers:

- source-plus-test changes producing TypeScript provider summaries without
  advisory source-without-test findings;
- source-heavy source-only changes producing TypeScript `source-heavy` and
  `source-without-test` advisory findings;
- broad TypeScript suppression counting through the public JSON payload.

This closes one maturation gap between patched fixture readers and real Git
diff behavior. It still does not justify blocking TypeScript reviewability
gates: more repository shapes and at least one external real-repo comparison are
still needed before any promotion beyond advisory output.

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
- which output formats are stable enough for exact repair facts;
- whether suppressions should remain advisory;
- which advisory threshold values stay low-noise across real repositories;
- which signals are too framework-specific for defaults;
- whether any abstraction makes Python less capable.

## Promotion Bar

TypeScript/JavaScript should not move toward supported status until it has:

- fixture evidence for common npm and pnpm project shapes;
- at least one real-repo comparison pass with acceptable noise;
- stable explicit-command behavior;
- clear doctor messages for missing commands and executables;
- structured repair facts only for stable outputs;
- documented unsupported package managers, runners, and frameworks;
- no blocking gates enabled by default.

Blocking reviewability policy is a later opt-in step. It is not part of this
maturation note.
