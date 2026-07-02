# Phase 100: TypeScript Provider Maturation

## Status

Complete.

## Goal

Make TypeScript/JavaScript the first serious non-Python provider maturation
track. The aim is to learn which behavior should become shared provider
infrastructure without pushing Node-specific assumptions into core.

## Scope

- Keep Python as the core/reference provider and preserve current behavior.
- Add TypeScript/JavaScript fixture evidence for common repository shapes:
  basic npm package, pnpm workspace, Vite/Vitest, Jest, generated folders,
  source-only changes, source-plus-test changes, dependency changes, config
  changes, and broad/narrow suppressions.
- Improve TypeScript/JavaScript repair facts only for stable, documented tool
  outputs.
- Add a running TypeScript provider maturation note that records what
  generalized cleanly and what stayed ecosystem-specific.
- Consider advisory TypeScript thresholds only after fixture and real-repo
  output prove low noise.

## Non-Goals

- No new ecosystem provider.
- No public plugin API.
- No TypeScript/JavaScript blocking gates.
- No package-manager autodetection until explicit-command behavior is proven.
- No changes to Python check names, commands, artifacts, thresholds, or
  profiles.

## Acceptance Criteria

- Provider docs state TypeScript/JavaScript is the first maturation candidate,
  not a supported provider at Python parity.
- TypeScript fixture tests cover representative source/test/generated/config,
  dependency, and suppression scenarios.
- TypeScript repair-fact additions are backed by stable sample outputs.
- Any TypeScript threshold names remain documented candidates, not active
  config fields.
- README/provider-status docs avoid overclaiming polyglot maturity.

## Future Codex Tasks

If an abstraction makes Python less capable, stop and redesign it. If a
TypeScript improvement pushes Node/package-manager assumptions into core, move
the behavior back behind the TypeScript provider.

## Result

Added TypeScript fixture-style reviewability tests covering source-plus-test
changes, source-only heavy changes, generated/build outputs, dependency files,
config files, and broad/narrow suppressions. Added TypeScript provider
maturation notes under `docs/case-studies/`.
