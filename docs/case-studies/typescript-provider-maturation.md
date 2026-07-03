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
standalone classifier. This proves users and agents see useful advisory output
without changing blocking verifier behavior.

## Advisory Threshold Evidence

Current fixture evidence supports considering advisory thresholds for:

- source-only TypeScript changes;
- source-heavy TypeScript changes by changed source files and changed source
  lines;
- broad TypeScript/JavaScript suppressions.

Current fixture evidence does not yet support blocking thresholds. It also does
not yet support package-manager autodetection, test-runner-specific defaults, or
framework-specific generated-file policy beyond the existing classifier.

Future advisory config names should stay TypeScript-owned and non-blocking until
real-repo output proves low noise. Candidate names:

```toml
[tool.agent_maintainer]
typescript_advisory_source_warn_files = 8
typescript_advisory_source_warn_lines = 300
typescript_advisory_broad_suppression_warn = 1
```

These names are documentation-only candidates. They are not implemented config
fields and must not be treated as active policy.

## Lessons To Capture

Use this page as the running implementation notebook while TypeScript matures.
Track:

- repository shapes that stayed low-noise;
- package-manager assumptions that stayed provider-specific;
- output formats stable enough for exact repair facts;
- suppressions that should remain advisory;
- signals that might eventually become configurable advisory thresholds;
- signals too framework-specific for defaults;
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

Blocking reviewability policy is a later opt-in step, not part of this
maturation note.
