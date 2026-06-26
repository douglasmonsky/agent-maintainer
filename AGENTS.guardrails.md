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

## File Inspection Safety

- Prefer `rg --files` or `git ls-files` when enumerating files to inspect.
- Restrict bulk reads to relevant text/source globs instead of every file under a tree.
- Do not read generated or binary artifacts unless the task explicitly targets them:
  `__pycache__`, `*.pyc`, `.venv`, `venv`, `.verify-logs`, `.coverage`,
  `coverage.xml`, `htmlcov`, `build`, and `dist`.
- Guardrail and hook subprocesses set `PYTHONDONTWRITEBYTECODE=1` by
  default. Set `AI_GUARDRAILS_WRITE_BYTECODE=true` only when explicitly
  debugging bytecode-cache behavior.
- When a broad command is unavoidable, exclude generated, binary, cache, and
  virtualenv paths before printing file contents.

## Active Configuration

- Mode: `fresh-strict`
- Source roots: `scripts`, `.codex/hooks`, `guardrail_lib`
- Test roots: `tests`
- Package paths: `scripts`, `.codex/hooks`, `guardrail_lib`
- Coverage source: `scripts`, `.codex/hooks`, `guardrail_lib`
- Architecture backend: `tach`
- Tests required: `true`
- Diagnostic artifacts: `enabled` at `.verify-logs`
- Source-without-test-change errors in profiles: `precommit`
- Source-only changes without test-file changes: `blocked`

## Verification Flow

- Trusted Codex hooks normally run fast checks after edits and the precommit profile
  before completion.
- Run the precommit profile manually when hooks are unavailable, after bypassing hooks,
  or when reproducing a hook failure:
  `python3 -m scripts.guardrail verify --profile precommit`.
- Run the full profile before merging larger changes or changing shared guardrail logic:
  `python3 -m scripts.guardrail verify --profile full`.
- After changing `[tool.ai_guardrails]`, run
  `python3 -m scripts.guardrail guidance` and `python3 -m scripts.guardrail doctor`.

## Thresholds To Preserve

- Total coverage floor: `80%`
- Changed-code coverage floor: `90%`
- File length limits: `500` physical lines, `375` source lines
- File length baseline: `disabled`
- Change budget warnings: `200` lines or `6` files
- Change budget blocks: `600` lines or `12` files
- New suppression budget: `1`
- Ruff McCabe complexity: `8`
- Xenon complexity: absolute `B`, modules `A`, average `A`
- Pyright mode: `standard`
- Interrogate floor: `80%`

## Optional Gates

- pip-audit: enabled with `-r config/dev-lock.txt`
- Secret scanning: enabled with `gitleaks` (profiles: full, ci; history: security)
- wemake-python-styleguide: `enabled`
- Interrogate: `enabled`

## Escape Hatches

- Prefer config changes over one-off command drift when repository layout changes.
- Keep temporary CLI or environment overrides out of committed config unless they are policy.
- Use `require_tests = false` only for repositories that intentionally have no tests.
- Use `allow_source_without_test_change = true` only when existing tests already cover the change.
- If a guardrail is wrong, make the smallest correction to the check, config, or docs.
