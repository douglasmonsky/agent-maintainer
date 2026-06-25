# AI maintainability guardrails for Python repositories

This is a drop-in kit for steering AI-assisted Python changes toward maintainable code. It focuses on automatic feedback, quiet reporting, and enforceable limits rather than relying on prompt reminders.

## What this kit enforces

| Concern | Enforcement |
|---|---|
| Oversized Python files | `scripts/check_file_lengths.py` |
| Huge or diffuse changes | `scripts/check_change_budget.py` |
| Broad suppressions | `scripts/check_suppression_budget.py` |
| Required repo layout | `scripts/guardrail.py verify` layout check |
| Style and simple defects | Ruff |
| Type discipline | Pyright |
| Tests and total coverage | Pytest + pytest-cov |
| Changed-code coverage in CI | diff-cover |
| Complexity | Radon reports + Xenon gate |
| Module/file length backup | Pylint `max-module-lines` |
| Fresh-repo strict style | wemake-python-styleguide, when explicitly enabled |
| Architecture boundaries | Import Linter, when `.importlinter` exists |
| Dependency hygiene | deptry |
| Dead code | vulture |
| Security checks | Bandit; pip-audit when explicitly enabled |
| Local enforcement | pre-commit |
| Final enforcement | GitHub Actions |
| AI-loop feedback | Codex `PostToolUse` and `Stop` hooks |

## Install

Copy these files into the root of a Python repository:

```text
AGENTS.md
justfile
.pre-commit-config.yaml
.codex/
.github/workflows/verify.yml
scripts/
config/
```

Install dev dependencies. With `uv`:

```bash
uv add --dev ruff pyright pytest pytest-cov coverage diff-cover hypothesis import-linter radon xenon pylint deptry vulture bandit pip-audit pre-commit wemake-python-styleguide
```

Or with pip:

```bash
python -m pip install -r config/dev-dependencies.txt
```

For the shortest local path with pip, run:

```bash
python3 scripts/guardrail.py bootstrap
```

This creates `.venv` when needed, installs `config/dev-dependencies.txt`, installs the pre-commit hook, and reports whether Codex hooks are configured.

Python 3.11+ is recommended. Python 3.10 and older require `tomli` in the same environment that runs the verifier. The Codex hooks prefer `.venv/bin/python` or `venv/bin/python` when present, so installing dev dependencies into a project virtualenv is the most reliable local setup.

Then merge `config/pyproject.guardrails.toml` into your `pyproject.toml`.

Copy the Pyright and Pylint examples if you want them active:

```bash
cp config/pyrightconfig.json pyrightconfig.json
cp config/pylintrc.example .pylintrc
```

For wemake-python-styleguide, copy and tune the flake8 example before enabling it:

```bash
cp config/flake8.wemake.example .flake8
```

For architecture contracts, copy and edit the Import Linter template:

```bash
cp config/importlinter.example .importlinter
# Then replace your_package with your actual root package.
```

Install local guardrail hooks:

```bash
python3 scripts/guardrail.py install
```

This keeps dependency installation separate and only installs the pre-commit hook when `pre-commit` is available. If you use Codex, review and trust the repo-local hooks through Codex's hook review flow.

## Configure paths

The verifier no longer assumes that every project uses `src/` and `tests/` silently. Defaults are still `src` and `tests`, but missing configured roots are reported as guardrail configuration failures in `precommit`, `full`, and `ci` profiles.

Preferred configuration lives in `pyproject.toml`:

```toml
[tool.ai_guardrails]
source_roots = ["src"]
test_roots = ["tests"]
package_paths = ["src"]
coverage_source = ["src"]
file_length_paths = ["src", "tests", "scripts", ".codex/hooks"]
vulture_paths = ["src", "tests", "scripts"]
require_tests = true
coverage_fail_under = 80
diff_cover_fail_under = 90
enable_pip_audit = false
enable_wemake = false
```

Set `require_tests = false` only for repositories where tests are intentionally unavailable. In that mode, pytest coverage and changed-code coverage are reported as explicit optional skips.

For a flat package layout, use something like:

```toml
[tool.ai_guardrails]
source_roots = ["my_package"]
test_roots = ["tests"]
package_paths = ["my_package"]
coverage_source = ["my_package"]
file_length_paths = ["my_package", "tests", "scripts", ".codex/hooks"]
vulture_paths = ["my_package", "tests", "scripts"]
```

Environment overrides are also supported:

```bash
GUARDRAILS_SOURCE_ROOTS=my_package,tools \
GUARDRAILS_TEST_ROOTS=tests \
GUARDRAILS_COVERAGE_SOURCE=my_package \
GUARDRAILS_PACKAGE_PATHS=my_package \
python3 scripts/guardrail.py verify --profile full
```

CLI overrides are available for one-off runs:

```bash
python3 scripts/guardrail.py verify --profile full \
  --source-root my_package \
  --test-root tests \
  --coverage-source my_package \
  --package-path my_package
```

## Commands

Quiet local verification:

```bash
python3 scripts/guardrail.py verify --profile full
```

One-command local bootstrap:

```bash
python3 scripts/guardrail.py bootstrap
```

Fast check after edits:

```bash
python3 scripts/guardrail.py verify --profile fast
```

Commit-level check:

```bash
python3 scripts/guardrail.py verify --profile precommit
```

CI-level check:

```bash
python3 scripts/guardrail.py verify --profile ci --base-ref origin/main --compare-branch origin/main
```

If you use `just`:

```bash
just bootstrap
just verify
just verify-fast
just verify-precommit
just verify-ci
```

## Output philosophy

The quiet verifier prints only:

```text
PASS
```

or a compact failure report:

```text
FAIL: 2 check(s) failed [full]

1. pyright
src/service.py:44:12: error: Type "None" is not assignable to "str"

2. file-length
src/runner.py:724 physical lines, 510 source lines (limits: 600 physical, 450 source)

Full logs are in .verify-logs/.
```

Optional integrations are explicit, not silent. For example, if `.importlinter` is absent or `pip-audit` is disabled, a passing full run may include:

```text
PASS
SKIPPED optional checks:
  import-linter: .importlinter is absent; architecture contracts are not configured
  pip-audit: disabled by default; enable with GUARDRAILS_ENABLE_PIP_AUDIT=1 or [tool.ai_guardrails].enable_pip_audit = true
```

Full raw output is stored in `.verify-logs/` to keep agent context small.

## Profiles

`fast` is designed for Codex `PostToolUse` after file edits. It runs cheap checks: file length, change budget, suppression budget, and Ruff. It still fails when required guardrail scripts or `.git` are missing, but it does not require configured source/test roots to exist yet.

`precommit` is designed for local commits and Codex final checks. It adds formatting, type checking, tests with coverage, and Xenon complexity gates. It fails if configured source, test, coverage, or package paths are missing, unless tests are explicitly disabled. When tests are disabled, pytest coverage is reported as an optional skip. The bundled pre-commit hook runs this profile with `--staged`, so diff budgets inspect staged changes only.

`full` is designed for local deep verification. It adds Radon reports, Pylint, Import Linter when configured, deptry, vulture, Bandit, and pip-audit when explicitly enabled.

`ci` is designed for GitHub Actions. It runs the full profile plus changed-code coverage through diff-cover. When tests are disabled, changed-code coverage is reported as an optional skip.

## Suggested thresholds

| Metric | Default |
|---|---:|
| Python file physical lines | 600 |
| Python file source lines | 450 |
| Ruff McCabe complexity | 10 |
| Xenon max absolute complexity | B |
| Xenon max module complexity | A |
| Xenon max average complexity | A |
| Total coverage | 80% |
| Changed-code coverage | 90% |
| New broad suppressions | blocked |
| New suppression comments per diff | 3 |
| Python source diff warning | 300 lines |
| Python source diff hard block | 800 lines |
| Python source files warning | 8 files |
| Python source files hard block | 20 files |

## pip-audit behavior

`pip-audit` is disabled by default in this kit. When enabled, it can query external vulnerability data and may audit unrelated active-environment packages if you run it without input files. Prefer a pinned input where possible:

```toml
[tool.ai_guardrails]
enable_pip_audit = true
pip_audit_args = ["-r", "requirements.txt"]
```

Or enable it only in CI with an environment variable:

```bash
GUARDRAILS_ENABLE_PIP_AUDIT=1 GUARDRAILS_PIP_AUDIT_ARGS="-r requirements.txt" python3 scripts/guardrail.py verify --profile ci
```

## wemake behavior

`wemake-python-styleguide` is disabled by default because it is intentionally rigid. Enable it for fresh repositories where you want strict style friction from day one:

```toml
[tool.ai_guardrails]
enable_wemake = true
```

Or enable it temporarily:

```bash
GUARDRAILS_ENABLE_WEMAKE=1 python3 scripts/guardrail.py verify --profile full
```

When enabled, the verifier runs `flake8 --require-plugins wemake-python-styleguide` over configured `package_paths`. For existing repositories, keep it off until you have a clean baseline or an explicit ratchet plan.

## Notes

Start strict for new repositories. For existing repositories, start with `fast` and `precommit`, then promote the heavier checks after you have a clean baseline.

This repository is configured to use the kit on itself, including `enable_wemake = true`. After changing guardrail code or docs, run `python3 scripts/guardrail.py verify --profile precommit`; for broader changes, run `python3 scripts/guardrail.py verify --profile full`.

Generated files are skipped by the file-length check when they contain common generated-file markers near the top. Lock files and binary assets are excluded from the change-budget check.

This kit is intentionally conservative about suppressions. It does not ban all suppressions, but it blocks broad or excessive suppressions because they are a common way for AI-assisted changes to hide real failures.
