# Tool map

## Everyday gates

`python3 -m scripts.guardrail` is the canonical entrypoint. Use `python3 -m scripts.guardrail bootstrap` for one-command local setup, `python3 -m scripts.guardrail doctor` for setup health, `python3 -m scripts.guardrail guidance` for generated agent-facing guidance, `python3 -m scripts.guardrail verify --profile precommit` for local completion checks, `python3 -m scripts.guardrail verify --profile full` for deeper review, and `python3 -m scripts.guardrail install` to install local hooks without reinstalling dependencies.

`doctor --strict` turns setup warnings into a nonzero exit. Use it after bootstrap and after pushing local commits when you want a clean health signal that includes git sync state.

`guidance --check` verifies that `AGENTS.guardrails.md` is current with
`[tool.ai_guardrails]`. In this repository's `fresh-strict` mode, `doctor`
reports stale generated guidance as a failure.

Ruff handles formatting, import order, linting, and McCabe complexity feedback.
The verifier preserves Ruff JSON as `.verify-logs/ruff.json` and prints compact
diagnostics instead of dumping raw JSON into terminal output. It is the fastest
feedback loop and should run after most edits.

Pyright enforces type discipline. The verifier runs it through a generated project config so `[tool.ai_guardrails].pyright_type_checking_mode` affects the actual Pyright invocation. Pyright JSON is also preserved as `.verify-logs/pyright.json` and listed in the verifier manifest.

Pytest and pytest-cov enforce behavior and coverage. The configured coverage
gate prevents untested new behavior from quietly entering the repository. The
verifier keeps root `coverage.xml` for diff-cover and writes
`.verify-logs/coverage.json` plus `.verify-logs/pytest-junit.xml` for structured
diagnostics and CI artifacts.

Verifier diagnostics write `.verify-logs/manifest.json` for machine-readable run
metadata and `.verify-logs/LAST_FAILURE.md` when the latest run fails. The
terminal output stays compact; agents should use these artifacts for command,
exit-code, threshold, log-path, and rerun context.
Codex hooks append local execution evidence to `.verify-logs/hooks.jsonl`, and
`doctor` reports the latest audited hook status.

## Maintainability gates

Radon reports cyclomatic complexity and maintainability metrics. Xenon converts complexity thresholds into a failing gate.

Pylint provides a backup for design smells, including module length through `max-module-lines`.

wemake-python-styleguide is an opt-in strictness gate for fresh repos and clean baselines. It runs only when `enable_wemake = true` or `GUARDRAILS_ENABLE_WEMAKE=1`, and the verifier requires the actual wemake plugin so plain flake8 cannot masquerade as the strict check.

Interrogate checks docstring coverage. It runs only when `enable_interrogate = true` or `GUARDRAILS_ENABLE_INTERROGATE=1`; use `interrogate_fail_under` as a ratchet floor rather than forcing a legacy repo to document every helper at once.

Tach and Import Linter are supported architecture boundary backends. `architecture_tool = "import-linter"` is the backward-compatible default. `architecture_tool = "tach"` runs a Tach config smoke check and then `tach check --exact`.

This repository uses Tach for its own guardrail script modules. Its `tach.toml` keeps entrypoints and orchestration depending inward on shared config, reporting, and model modules, and uses `root_module = "forbid"` so source files cannot drift outside explicit modules.

## Diff hygiene gates

The file-length check stops giant files. In `legacy-ratchet`, it can use `file_length_baseline` so old oversized files are tolerated only while they stay unchanged or improve; new and worsened oversized files fail.

The change-budget check prevents huge or overly diffuse changes from becoming a single opaque commit. It uses configured `source_roots` and `test_roots`, not hard-coded `src/` and `tests/`. In pre-commit, `--staged` limits diff-budget checks to the staged patch. Nonfatal warnings are shown in the aggregate verifier output; in `fresh-strict`, source changes without configured test-file changes fail in `precommit` unless explicitly allowed.

The suppression-budget check prevents broad `noqa`, `type: ignore`, `pylint: disable`, and `pragma: no cover` usage from hiding quality failures.

## Cleanup and dependency gates

deptry catches unused, missing, and transitive dependency problems.

vulture finds likely dead Python code.

Bandit scans Python source for common security issues. The verifier preserves
Bandit JSON as `.verify-logs/bandit.json` and prints compact findings instead
of dumping raw JSON into terminal output.

pip-audit checks Python packages for known vulnerabilities. It is disabled by default in this kit because it may use network access and, without an input file, can audit unrelated packages in the active environment. Enable it explicitly with pinned input, such as `pip_audit_args = ["-r", "config/dev-lock.txt"]`. In `fresh-strict`, enabling pip-audit without pinned args is a failure.

`config/dev-dependencies.txt` is the human-edited dependency input. `config/dev-lock.txt` is the pinned install and audit artifact when present; bootstrap and CI prefer it automatically.

## Configuration model

Shared path configuration is read from `[tool.ai_guardrails]` in `pyproject.toml`, then `GUARDRAILS_*` environment variables, then CLI flags. The important fields are:

```toml
[tool.ai_guardrails]
mode = "custom"
architecture_tool = "import-linter"
enable_interrogate = false
interrogate_fail_under = 80
source_roots = ["src"]
test_roots = ["tests"]
package_paths = ["src"]
coverage_source = ["src"]

[tool.ai_guardrails.diagnostics]
enabled = true
log_dir = ".verify-logs"
```

Mode can be `custom`, `legacy-ratchet`, or `fresh-strict`. Built-in defaults apply first, then mode defaults, then explicit pyproject fields, environment variables, and CLI flags.

Missing required roots fail in `precommit`, `full`, and `ci`; optional integrations are reported as skipped. In `fresh-strict` mode with `architecture_tool = "tach"`, `tach.toml` must exist and use `root_module = "forbid"`.

`doctor` checks that verifier diagnostics are coherent: logs exist, the manifest
is present and newer than the latest raw log, manifest-referenced logs and
artifacts still exist, and `LAST_FAILURE.md` matches the pass/fail state of the
latest manifest. It also checks the Codex hook audit trail when repo-local hooks
are enabled.
