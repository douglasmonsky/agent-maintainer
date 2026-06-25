# Review-driven changes in this revision

This revision addresses the main review findings from the first package.

## Required checks no longer skip silently

`python -m scripts.guardrail verify` now distinguishes required guardrail assets from optional integrations.

Required failures include missing helper scripts, missing `.git` for diff-based checks, missing configured source roots in precommit/full/ci, missing configured test roots when tests are required, missing coverage sources, missing package paths, and missing executables for selected required checks.

Optional skips are reported explicitly. Currently this applies to absent `.importlinter`, disabled `pip-audit`, and coverage checks when `require_tests = false`.

## Configurable repository layout

Shared configuration now lives in `scripts/guardrail_config.py` and is read from `[tool.ai_guardrails]`, environment variables, and CLI overrides.

Supported path settings include:

```toml
source_roots = ["src"]
test_roots = ["tests"]
package_paths = ["src"]
coverage_source = ["src"]
file_length_paths = ["src", "tests", "scripts", ".codex/hooks"]
vulture_paths = ["src", "tests", "scripts"]
```

The change-budget check now uses configured source and test roots instead of hard-coded `src/` and `tests/`.

## Codex hooks are repo-root safe after launch

The hook scripts now derive:

```python
repo_root = Path(__file__).resolve().parents[2]
```

They run `python -m scripts.guardrail verify` with `cwd=repo_root`. When `.venv/bin/python` or `venv/bin/python` exists, hooks use that interpreter for the verifier.

## Bootstrap command and staged pre-commit diffs

`python3 -m scripts.guardrail install` installs the local pre-commit hook and reports Codex hook configuration.

The pre-commit hook calls `python3 -m scripts.guardrail verify --profile precommit --staged`, so the change-budget and suppression-budget checks inspect the staged patch instead of unrelated working-tree edits.

## CI no longer masks editable-install failures

The GitHub Actions workflow now skips editable install only when no package metadata exists. If package metadata is present, `python -m pip install -e .` must succeed.

## pip-audit is explicit

`pip-audit` is disabled by default. Enable it with:

```toml
enable_pip_audit = true
pip_audit_args = ["-r", "requirements.txt"]
```

or:

```bash
GUARDRAILS_ENABLE_PIP_AUDIT=1 GUARDRAILS_PIP_AUDIT_ARGS="-r requirements.txt"
```

The README now documents the network/flakiness/privacy implications.
