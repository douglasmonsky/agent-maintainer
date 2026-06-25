# Tool map

## Everyday gates

`scripts/guardrail.py` is the canonical entrypoint. Use `python3 scripts/guardrail.py verify --profile precommit` for local completion checks, `python3 scripts/guardrail.py verify --profile full` for deeper review, and `python3 scripts/guardrail.py install` to install local hooks.

Ruff handles formatting, import order, linting, and McCabe complexity feedback. It is the fastest feedback loop and should run after most edits.

Pyright enforces type discipline. It prevents vague interfaces and catches many integration mistakes before runtime.

Pytest and pytest-cov enforce behavior and coverage. The configured coverage gate prevents untested new behavior from quietly entering the repository.

## Maintainability gates

Radon reports cyclomatic complexity and maintainability metrics. Xenon converts complexity thresholds into a failing gate.

Pylint provides a backup for design smells, including module length through `max-module-lines`.

wemake-python-styleguide is an opt-in strictness gate for fresh repos and clean baselines. It runs only when `enable_wemake = true` or `GUARDRAILS_ENABLE_WEMAKE=1`, and the verifier requires the actual wemake plugin so plain flake8 cannot masquerade as the strict check.

Import Linter enforces architectural boundaries once `.importlinter` is configured for the repository. The verifier reports it as an optional skip when `.importlinter` is absent rather than silently pretending the architecture gate ran.

## Diff hygiene gates

The file-length check stops giant files.

The change-budget check prevents huge or overly diffuse changes from becoming a single opaque commit. It uses configured `source_roots` and `test_roots`, not hard-coded `src/` and `tests/`. In pre-commit, `--staged` limits diff-budget checks to the staged patch.

The suppression-budget check prevents broad `noqa`, `type: ignore`, `pylint: disable`, and `pragma: no cover` usage from hiding quality failures.

## Cleanup and dependency gates

deptry catches unused, missing, and transitive dependency problems.

vulture finds likely dead Python code.

Bandit scans Python source for common security issues.

pip-audit checks Python packages for known vulnerabilities. It is disabled by default in this kit because it may use network access and, without an input file, can audit unrelated packages in the active environment. Enable it explicitly with pinned input, such as `pip_audit_args = ["-r", "requirements.txt"]`.

## Configuration model

Shared path configuration is read from `[tool.ai_guardrails]` in `pyproject.toml`, then `GUARDRAILS_*` environment variables, then CLI flags. The important fields are:

```toml
[tool.ai_guardrails]
source_roots = ["src"]
test_roots = ["tests"]
package_paths = ["src"]
coverage_source = ["src"]
```

Missing required roots fail in `precommit`, `full`, and `ci`; optional integrations are reported as skipped.
