# Phase 101: TypeScript Advisory Threshold Evidence

## Status

Complete.

## Goal

Use Phase 100 TypeScript fixture evidence to decide which advisory signals are
stable enough to become configurable TypeScript thresholds. This phase keeps
TypeScript/JavaScript advisory-only.

## Scope

- Review TypeScript fixture output for `assess reviewability` source-heavy,
  source-without-test, dependency/config, generated-output, and suppression
  scenarios.
- Add explicit-command TypeScript examples that show safe npm and pnpm setup
  without implying package-manager autodetection.
- Draft advisory TypeScript threshold names and semantics only where evidence
  supports them.
- Keep threshold behavior non-blocking and disabled in verifier profiles.
- Update TypeScript provider maturation notes with evidence decisions.

## Non-Goals

- No new ecosystem provider.
- No public plugin API.
- No TypeScript blocking gates.
- No package-manager autodetection.
- No starter files that imply universal JavaScript project support.
- No changes to Python check names, commands, artifacts, thresholds, or
  profiles.

## Acceptance Criteria

- TypeScript provider docs include explicit-command examples for at least npm
  and pnpm without guessing package-manager behavior.
- TypeScript maturation notes state which advisory signals are stable enough for
  future configurable thresholds and which remain too noisy.
- Any proposed threshold names are documented as future advisory config, not
  implemented blocking policy.
- No verifier profile starts failing because of TypeScript advisory findings.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess tests/ecosystems/test_typescript_classification.py tests/ecosystems/test_typescript_suppressions.py tests/ecosystems/test_typescript_provider.py -q`

## Result

Updated TypeScript provider docs and maturation notes with advisory-threshold
evidence and documentation-only candidate threshold names. No runtime config
fields, blocking gates, package-manager autodetection, or Python behavior
changes were added.
