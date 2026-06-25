# Generated Guardrail Guidance

This file is generated from `[tool.ai_guardrails]` by
`python3 -m scripts.guardrail guidance`. Do not edit it by hand; update
configuration first, then regenerate it.

## Operating Intent

- Prefer small, coherent commits that keep guardrail feedback easy to review.
- Keep source, tests, documentation, and configuration moving together.
- Treat failing checks as design feedback before reaching for suppressions.
- Preserve the configured architecture boundaries instead of adding imports around them.
- Add or update tests for behavior changes unless tests are explicitly disabled.

## Active Configuration

- Mode: `fresh-strict`
- Source roots: `scripts`, `.codex/hooks`
- Test roots: `tests`
- Package paths: `scripts`, `.codex/hooks`
- Coverage source: `scripts`, `.codex/hooks`
- Architecture backend: `tach`
- Tests required: `true`

## Required Workflow

- Before finishing a code task, run
  `python3 -m scripts.guardrail verify --profile precommit`.
- Before merging a larger change, run
  `python3 -m scripts.guardrail verify --profile full`.
- After changing `[tool.ai_guardrails]`, run
  `python3 -m scripts.guardrail guidance` and `python3 -m scripts.guardrail doctor`.

## Thresholds To Preserve

- Total coverage floor: `80%`
- Changed-code coverage floor: `90%`
- File length limits: `500` physical lines, `375` source lines
- Change budget warnings: `200` lines or `6` files
- Change budget blocks: `600` lines or `12` files
- New suppression budget: `1`
- Ruff McCabe complexity: `8`
- Xenon complexity: absolute `B`, modules `A`, average `A`
- Pyright mode: `standard`
- Interrogate floor: `80%`

## Optional Gates

- pip-audit: enabled with `-r config/dev-lock.txt`
- wemake-python-styleguide: `enabled`
- Interrogate: `enabled`

## Escape Hatches

- Prefer config changes over one-off command drift when repository layout changes.
- Keep temporary CLI or environment overrides out of committed config unless they are policy.
- Use `require_tests = false` only for repositories that intentionally have no tests.
- If a guardrail is wrong, make the smallest correction to the check, config, or docs.
