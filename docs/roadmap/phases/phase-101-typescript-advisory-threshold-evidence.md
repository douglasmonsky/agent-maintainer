# Phase 101: TypeScript Advisory Threshold Evidence

## Status

Complete.

## Goal

Use the Phase 100 TypeScript fixture evidence to decide which advisory signals
are stable enough to become configurable TypeScript thresholds. This phase keeps
TypeScript/JavaScript advisory-only and keeps Go frozen as a thin experimental
canary.

## Scope

- Review TypeScript fixture output from `assess reviewability` for source-heavy,
  source-without-test, dependency/config, generated-output, and suppression
  scenarios.
- Add explicit-command TypeScript examples that show safe npm and pnpm setup
  without implying package-manager autodetection.
- Draft advisory TypeScript threshold names and semantics only after evidence
  supports them.
- Keep threshold behavior non-blocking and disabled from verifier profiles.
- Keep Go limited to registry/classifier/advisory compatibility tests.
- Update TypeScript provider maturation notes with evidence and decisions.

## Non-Goals

- No new ecosystem provider.
- No public plugin API.
- No Go depth expansion.
- No TypeScript blocking gates.
- No package-manager autodetection.
- No starter files that imply universal JavaScript project support.
- No changes to Python check names, commands, artifacts, thresholds, or profiles.

## Acceptance Criteria

- TypeScript provider docs include explicit-command examples for at least npm and
  pnpm without guessing package-manager behavior.
- TypeScript maturation notes state which advisory signals are stable enough to
  consider for configurable thresholds and which remain too noisy.
- Any proposed threshold names are documented as future advisory config, not
  implemented as blocking policy.
- Go documentation still says Go is canary-only.
- No verifier profile starts failing because of TypeScript advisory findings.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess tests/ecosystems/test_typescript_classification.py tests/ecosystems/test_typescript_suppressions.py tests/ecosystems/test_typescript_provider.py -q`
- `npx --no-install markdownlint-cli2 docs/typescript-javascript-provider.md docs/case-studies/typescript-provider-maturation.md docs/roadmap/phases/phase-101-typescript-advisory-threshold-evidence.md`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`

## Notes For Future Codex Tasks

Do not implement thresholds just because names are drafted. Add real behavior
only after fixture output and at least one real-repo comparison show low-noise
signals. If a TypeScript threshold would require Node-specific logic in core,
move the logic behind the TypeScript provider or defer it.

## Result

Added npm, pnpm, and Vite/Vitest explicit-command examples to the TypeScript
provider documentation. Updated TypeScript provider maturation notes with
advisory-threshold evidence and documentation-only candidate threshold names. No
runtime config fields, blocking gates, package-manager autodetection, Go depth,
or Python behavior changes were added.
