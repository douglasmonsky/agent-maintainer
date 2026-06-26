# AI maintainability guardrails for Python repositories

This is a drop-in kit for steering AI-assisted Python changes toward maintainable code. It focuses on automatic feedback, quiet reporting, and enforceable limits rather than relying on prompt reminders.

## What this kit enforces

| Concern | Enforcement |
|---|---|
| Oversized Python files | `scripts/check_file_lengths.py` |
| Huge or diffuse changes | `scripts/check_change_budget.py` |
| Broad suppressions | `scripts/check_suppression_budget.py` |
| Required repo layout | `python -m scripts.guardrail verify` layout check |
| Style and simple defects | Ruff |
| Type discipline | Pyright |
| Tests and total coverage | Pytest + pytest-cov |
| Changed-code coverage in CI | diff-cover |
| Mutation testing | Mutmut, manual profile only |
| Docstring coverage | Interrogate, when explicitly enabled |
| Complexity | Radon reports + Xenon gate |
| Module/file length backup | Pylint `max-module-lines` |
| Fresh-repo strict style | wemake-python-styleguide, when explicitly enabled |
| Architecture boundaries | Tach or Import Linter, when configured |
| Dependency hygiene | deptry |
| Dead code | vulture |
| Security checks | Bandit; pip-audit when explicitly enabled; optional Gitleaks secret scanning |
| GitHub Actions checks | actionlint and zizmor when workflows exist |
| Docs/config hygiene | markdownlint-cli2, yamllint, Taplo, optional check-jsonschema |
| Local enforcement | pre-commit |
| Final enforcement | GitHub Actions |
| AI-loop feedback | Codex `PostToolUse` and `Stop` hooks |

## Install

Copy these files into the root of a Python repository:

```text
AGENTS.md
justfile
package.json
package-lock.json
.pre-commit-config.yaml
.codex/
.github/workflows/verify.yml
scripts/
config/
```

Install dev dependencies. With `uv`:

```bash
uv add --dev ruff pyright pytest pytest-cov coverage diff-cover hypothesis mutmut import-linter interrogate tach radon xenon pylint deptry vulture bandit pip-audit yamllint check-jsonschema actionlint-py zizmor pre-commit wemake-python-styleguide
```

Or with pip:

```bash
python -m pip install -r config/dev-lock.txt
```

For the shortest local path with pip, run:

```bash
python3 -m scripts.guardrail bootstrap
```

This creates `.venv` when needed, installs Python package guardrail tools from
`config/dev-lock.txt` when present, falls back to `config/dev-dependencies.txt`,
installs the pre-commit hook, and reports whether Codex hooks are configured.
It does not install external binaries, GitHub Actions-only tools, or manual
optional tools; `doctor` reports those capability states separately. This repo
enables Gitleaks secret scanning, so install it locally with `brew install
gitleaks` on macOS when running `full`, `ci`, or `security` profiles. CI
installs the pinned external binary through Go.

This repo also enables Markdown/TOML hygiene tools through `package-lock.json`:

```bash
npm ci
```

Keep `config/dev-dependencies.txt` as the human-edited dependency input. Refresh the pinned lock after changing it:

```bash
python3 -m scripts.guardrail bootstrap
.venv/bin/python -m pip freeze --exclude-editable | sort > config/dev-lock.txt
```

Python 3.11+ is recommended. Python 3.10 and older require `tomli` in the same environment that runs the verifier. The Codex hooks prefer `.venv/bin/python` or `venv/bin/python` when present, so installing dev dependencies into a project virtualenv is the most reliable local setup.

Check setup health after bootstrap:

```bash
python3 -m scripts.guardrail doctor
python3 -m scripts.guardrail doctor --strict
```

`doctor` reports compact `PASS`, `WARN`, and `FAIL` rows with a stable state
label: `active`, `disabled`, `not applicable`, `missing`, or `unsafe config`.
It covers Python version, tool capabilities, architecture backend, active
thresholds, configured roots, test availability, pre-commit installation, Codex
hook config, optional gates, canonical command wiring, git state, and recent
verification logs. By default only hard failures exit nonzero; `--strict` also
exits nonzero on warnings. JSON output includes `state` and `hint` fields for
setup tooling.

Then merge `config/pyproject.guardrails.toml` into your `pyproject.toml`.

Generate agent-facing guidance from the resolved guardrail config:

```bash
python3 -m scripts.guardrail guidance
python3 -m scripts.guardrail guidance --check
```

The generated `AGENTS.guardrails.md` sidecar summarizes the active mode, roots,
thresholds, enabled gates, and required commands. Keep human-written guidance in
`AGENTS.md`; regenerate the sidecar after changing `[tool.ai_guardrails]`.

Copy the Pyright and Pylint examples if you want them active:

```bash
cp config/pyrightconfig.json pyrightconfig.json
cp config/pylintrc.example .pylintrc
```

For wemake-python-styleguide, copy and tune the flake8 example before enabling it:

```bash
cp config/flake8.wemake.example .flake8
```

For architecture contracts, use Tach or Import Linter. Tach is the preferred strict
option for fresh repositories:

```bash
cp config/tach.example.toml tach.toml
# Then replace your_package with your actual root package.
```

Pair it with:

```toml
[tool.ai_guardrails]
architecture_tool = "tach"
```

For fresh-strict Tach, keep `root_module = "forbid"` and run `tach check --exact`.
The verifier enforces that strict root setting when `mode = "fresh-strict"` and
`architecture_tool = "tach"`.

Import Linter remains supported and is still the default-compatible option:

```bash
cp config/importlinter.example .importlinter
# Then replace your_package with your actual root package.
```

Install local guardrail hooks:

```bash
python3 -m scripts.guardrail install
```

This keeps dependency installation separate and only installs the pre-commit hook when `pre-commit` is available. If you use Codex, review and trust the repo-local hooks through Codex's hook review flow.

## Configure paths

The verifier no longer assumes that every project uses `src/` and `tests/` silently. Defaults are still `src` and `tests`, but missing configured roots are reported as guardrail configuration failures in `precommit`, `full`, and `ci` profiles.

Preferred configuration lives in `pyproject.toml`:

```toml
[tool.ai_guardrails]
# Optional: custom (default), legacy-ratchet, or fresh-strict.
# mode = "custom"
# Optional: import-linter (default) or tach.
# architecture_tool = "import-linter"
source_roots = ["src"]
test_roots = ["tests"]
package_paths = ["src"]
coverage_source = ["src"]
file_length_paths = ["src", "tests", "scripts", ".codex/hooks"]
file_length_baseline = ""
vulture_paths = ["src", "tests", "scripts"]
require_tests = true
coverage_fail_under = 80
diff_cover_fail_under = 90
source_without_test_change_error_profiles = ["precommit"]
allow_source_without_test_change = false
enable_pip_audit = false
enable_secret_scanning = false
secret_scanner = "gitleaks"
secret_scan_profiles = ["full", "ci"]
secret_scan_history_profiles = ["security"]
enable_wemake = false
enable_interrogate = false
interrogate_fail_under = 80
enable_markdownlint = false
markdownlint_paths = ["**/*.md"]
enable_yamllint = false
yamllint_paths = [".github/workflows", ".github/dependabot.yml", ".pre-commit-config.yaml", "*.yml", "*.yaml"]
enable_taplo = false
taplo_paths = ["*.toml", "config/*.toml"]
enable_check_jsonschema = false
# Example: check_jsonschema_args = ["--builtin-schema", "vendor.github-workflows", ".github/workflows/verify.yml"]
```

Use `mode = "fresh-strict"` for new repositories where strict checks should block from day one. Use `mode = "legacy-ratchet"` for existing repositories where heavy gates should stay opt-in while the repo adopts changed-file and baseline discipline. In `legacy-ratchet`, `file_length_baseline` defaults to `.guardrails/file-length-baseline.json`.

See `docs/fresh-strict.md` and `docs/legacy-ratchet.md` for preset details.

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
GUARDRAILS_ARCHITECTURE_TOOL=tach \
python3 -m scripts.guardrail verify --profile full
```

CLI overrides are available for one-off runs:

```bash
python3 -m scripts.guardrail verify --profile full \
  --source-root my_package \
  --test-root tests \
  --coverage-source my_package \
  --package-path my_package \
  --architecture-tool tach
```

## Commands

Quiet local verification:

```bash
python3 -m scripts.guardrail verify --profile full
```

One-command local bootstrap:

```bash
python3 -m scripts.guardrail bootstrap
```

Setup diagnostics:

```bash
python3 -m scripts.guardrail doctor --strict
```

Generate or check agent guidance:

```bash
python3 -m scripts.guardrail guidance
python3 -m scripts.guardrail guidance --check
```

Fast check after edits:

```bash
python3 -m scripts.guardrail verify --profile fast
```

Commit-level check:

```bash
python3 -m scripts.guardrail verify --profile precommit
```

CI-level check:

```bash
python3 -m scripts.guardrail verify --profile ci --base-ref origin/main --compare-branch origin/main
```

If you use `just`:

```bash
just bootstrap
just doctor
just guidance
just guidance-check
just verify
just verify-fast
just verify-precommit
just verify-ci
```

## More docs

- `docs/fresh-strict.md`: new-repo strictness preset.
- `docs/legacy-ratchet.md`: existing-repo adoption path.
- `docs/codex-hooks.md`: hook behavior and trust review.
- `docs/troubleshooting.md`: setup, lock, and verification failures.
- `docs/tool-map.md`: compact map of the included tools.
- `docs/ROADMAP.md`: tracked product hardening roadmap.

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

Passing runs can also surface warnings without failing. For example, a large but
non-blocking staged change may print:

```text
PASS
WARNINGS:
  change-budget: Change budget warnings:
  WARN: Large Python source diff: 225 changed lines (warning threshold: 200).
```

Optional integrations are explicit, not silent. For example, if architecture contracts are absent or `pip-audit` is disabled, a passing full run may include:

```text
PASS
SKIPPED optional checks:
  import-linter: .importlinter is absent; architecture contracts are not configured
  pip-audit: disabled by default; enable with GUARDRAILS_ENABLE_PIP_AUDIT=1 or [tool.ai_guardrails].enable_pip_audit = true
  interrogate: disabled by default; enable with GUARDRAILS_ENABLE_INTERROGATE=1 or [tool.ai_guardrails].enable_interrogate = true
```

When `architecture_tool = "tach"` is selected outside `fresh-strict`, absent
`tach.toml` is reported the same way. In `fresh-strict`, missing or permissive
Tach config is a failure.

Full raw output is stored in `.verify-logs/` to keep agent context small.
Guardrail subprocesses disable Python bytecode writes by default to avoid
generated cache files entering agent context accidentally.

## Profiles

`fast` is designed for Codex `PostToolUse` after file edits. It runs cheap checks: file length, change budget, suppression budget, and Ruff. It still fails when required guardrail scripts or `.git` are missing, but it does not require configured source/test roots to exist yet. In `legacy-ratchet`, file-length failures are compared against the configured baseline so existing oversized files pass unless they worsen.

`precommit` is designed for local commits and Codex final checks. It adds formatting, type checking, tests with coverage, and Xenon complexity gates. It fails if configured source, test, coverage, or package paths are missing, unless tests are explicitly disabled. When tests are disabled, pytest coverage is reported as an optional skip. The bundled pre-commit hook runs this profile with `--staged`, so diff budgets inspect staged changes only. In `fresh-strict`, source changes without configured test-file changes fail in `precommit` unless `allow_source_without_test_change = true` is set for an already-covered change.

`full` is designed for local deep verification. It adds Radon reports, Pylint, Tach or Import Linter when configured, Interrogate when enabled, deptry, vulture, Bandit, pip-audit when explicitly enabled, and secret scanning when configured.

`ci` is designed for GitHub Actions. It runs the full profile plus changed-code coverage through diff-cover. When tests are disabled, changed-code coverage is reported as an optional skip. The source/test-file-change heuristic remains nonfatal in CI unless `source_without_test_change_error_profiles` explicitly includes `ci`.

`security` is a manual security profile for checks such as full-history secret scans.

`manual` is reserved for slow or expensive opt-in checks such as mutation testing and SBOM generation. It is separate from `full` so normal local deep verification does not become unexpectedly slow.

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

## Notes

Start strict for new repositories. For existing repositories, start with `fast` and `precommit`, then promote the heavier checks after you have a clean baseline.

This repository is configured to use the kit on itself, including `enable_wemake = true`. After changing guardrail code or docs, run `python3 -m scripts.guardrail verify --profile precommit`; for broader changes, run `python3 -m scripts.guardrail verify --profile full`.

This repository also keeps the normally optional hardening gates active for itself: tests are required, `tach.toml` defines the guardrail-script dependency layers with `root_module = "forbid"`, Interrogate enforces an 80% docstring-coverage ratchet, `pip-audit` runs against `config/dev-lock.txt`, Mutmut runs in the manual profile, and Gitleaks secret scanning runs in `full`, `ci`, and manual `security` profiles.

`AGENTS.guardrails.md` is generated for this repository and should be refreshed
with `python3 -m scripts.guardrail guidance` whenever `[tool.ai_guardrails]`
changes.

Generated files are skipped by the file-length check when they contain common generated-file markers near the top. Lock files and binary assets are excluded from the change-budget check.

This kit is intentionally conservative about suppressions. It does not ban all suppressions, but it blocks broad or excessive suppressions because they are a common way for AI-assisted changes to hide real failures.
