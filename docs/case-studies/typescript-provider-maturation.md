# TypeScript Provider Maturation Notes

These notes track how TypeScript/JavaScript becomes the first serious
non-Python provider maturation target. The goal is to learn what should become
shared provider infrastructure without forcing Node-specific assumptions into
core.

## Current Posture

- Python remains the core/reference provider.
- TypeScript/JavaScript is the first non-Python provider to mature beyond thin
  command execution.
- Go remains a thin experimental canary. It should keep registry, classifier,
  doctor, and advisory-report compatibility honest without adding Go depth in
  parallel.
- No TypeScript/JavaScript reviewability signal is blocking yet.

## Fixture Evidence

Phase 100 adds TypeScript reviewability fixtures for:

- source-plus-test changes that should stay low-noise;
- source-only heavy changes that should produce advisory findings;
- generated and build output paths that should not inflate source/test signals;
- dependency files such as `package-lock.json` and `pnpm-lock.yaml`;
- config files such as `vite.config.ts` and `next.config.js`;
- broad and narrow suppressions.

The fixtures intentionally exercise `assess reviewability` rather than a
standalone classifier. That proves users and agents see useful advisory output
without changing blocking verifier behavior.

## Lessons To Capture

Use this page as a running implementation notebook while TypeScript matures.

Track:

- which repository shapes are low-noise;
- which package-manager assumptions stayed provider-specific;
- which output formats are stable enough for exact repair facts;
- which suppressions should remain advisory;
- which signals might eventually become configurable advisory thresholds;
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

Blocking reviewability policy is a later opt-in step, not part of this
maturation note.
