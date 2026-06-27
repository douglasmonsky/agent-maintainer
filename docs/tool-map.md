# Tool map

## Everyday gates

`python3 -m agent_maintainer` is the canonical entrypoint. Editable installs also provide `agent-maintainer` for interactive use, but committed hooks and CI should prefer the module command. Use `python3 -m agent_maintainer init --track core` for minimum package-first adoption, `python3 -m agent_maintainer init --track agent` when Codex or other agents actively edit the repo, and `python3 -m agent_maintainer init --track hardening` when optional docs/config hygiene files should also be generated. Use `python3 -m agent_maintainer bootstrap` for one-command local setup, `python3 -m agent_maintainer doctor` for setup health, `python3 -m agent_maintainer guidance` for generated agent-facing guidance, `python3 -m agent_maintainer verify --profile precommit` for local completion checks, `python3 -m agent_maintainer verify --profile full` for deeper review, `python3 -m agent_maintainer verify --profile manual` for slow opt-in checks, and `python3 -m agent_maintainer install` to install local hooks without reinstalling dependencies.

`doctor --strict` turns setup warnings into a nonzero exit. Use it after bootstrap and after pushing local commits when you want a clean health signal that includes git sync state.

The `manual` profile is intentionally separate from `full`. Put slow, expensive, or artifact-producing checks there so normal local deep verification stays predictable.

`just release-check` is intentionally release-only. It opts into tests marked
`release`, builds wheel and sdist artifacts in a temporary directory, and
installs declared extras in clean virtual environments without `--no-deps`.
Run it before tagging or publishing, not during the normal precommit loop.

`doctor` uses a tool capability model so setup failures distinguish Python
package commands, external binaries, GitHub Actions-only tools, and manual
optional tools. Bootstrap installs the Python package tools from the dependency
lock/input; it reports but does not install the other capability classes.

Doctor rows include a stable setup state: `active`, `disabled`,
`not applicable`, `missing`, or `unsafe config`. JSON output includes `state`
and `hint` fields so setup tooling can offer remediation without parsing prose.
Doctor also reports the active architecture backend and active thresholds for
coverage, diff-cover, Interrogate, complexity, and file length.

`guidance --check` verifies that `AGENTS.agent-maintainer.md` is current with
`[tool.agent_maintainer]`. In this repository's `fresh-strict` mode, `doctor`
reports stale generated guidance as a failure.

Ruff handles formatting, import order, linting, and McCabe complexity feedback.
The verifier preserves Ruff JSON as `.verify-logs/ruff.json` and prints compact
diagnostics instead of dumping raw JSON into terminal output. It is the fastest
feedback loop and should run after most edits.

Pyright enforces type discipline. The verifier runs it through a generated project config so `[tool.agent_maintainer].pyright_type_checking_mode` affects the actual Pyright invocation. Pyright JSON is also preserved as `.verify-logs/pyright.json` and listed in the verifier manifest.

Pytest and pytest-cov enforce behavior and coverage. The configured coverage
gate prevents untested new behavior from quietly entering the repository. The
verifier keeps root `coverage.xml` for diff-cover and writes
`.verify-logs/coverage.json` plus `.verify-logs/pytest-junit.xml` for structured
diagnostics and CI artifacts.

Mutmut provides mutation testing in the `manual` profile only. It is disabled by
default for drop-in use; enable it with `enable_mutmut = true` and configure
`mutmut_args` plus `[tool.mutmut]` source/test paths for nonstandard layouts.
The verifier runs Mutmut through `agent_maintainer.runners.mutmut`, which removes the
generated `mutants` directory after successful runs. Set
`AGENT_MAINTAINER_KEEP_MUTANTS=true` only when explicitly debugging mutation
artifacts. Mutmut requires fork support, so native Windows users should run it
inside WSL.

Verifier diagnostics write `.verify-logs/manifest.json` for machine-readable run
metadata and `.verify-logs/LAST_FAILURE.md` when the latest run fails. The
terminal output stays compact; agents should use these artifacts for command,
exit-code, threshold, log-path, and rerun context.
Codex hooks append local execution evidence to `.verify-logs/hooks.jsonl`, and
`doctor` reports the latest audited hook status.

## Maintainability gates

Radon reports cyclomatic complexity and maintainability metrics. Xenon converts complexity thresholds into a failing gate.

Pylint provides a backup for design smells, including module length through `max-module-lines`.

wemake-python-styleguide is an opt-in strictness gate for fresh repos and clean baselines. It runs only when `enable_wemake = true` or `AGENT_MAINTAINER_ENABLE_WEMAKE=1`, and the verifier requires the actual wemake plugin so plain flake8 cannot masquerade as the strict check.

Interrogate checks docstring coverage. It runs only when `enable_interrogate = true` or `AGENT_MAINTAINER_ENABLE_INTERROGATE=1`; use `interrogate_fail_under` as a ratchet floor rather than forcing a legacy repo to document every helper at once.

Tach and Import Linter are supported architecture boundary backends. `architecture_tool = "import-linter"` is the backward-compatible default. `architecture_tool = "tach"` runs a Tach config check and then `tach check --exact`.

This repository uses Tach for its own Agent Maintainer modules. Its `tach.toml` keeps entrypoints and orchestration depending inward on shared config, reporting, and model modules. In strict mode, the config check also requires each non-init Python source file under Tach's checked roots to appear explicitly in a Tach module entry, and each configured module entry must still resolve to source, so broad parent modules and stale references cannot hide ownership drift.

## Diff hygiene gates

The file-length check stops giant files. In `legacy-ratchet`, it can use `file_length_baseline` so old oversized files are tolerated only while they stay unchanged or improve; new and worsened oversized files fail.

The structure-cohesion check warns when one folder accumulates many Python files
and uses regex/layer hints to point at likely split candidates. It is advisory by
default and blocks only at the configured block threshold in `fresh-strict`.
Tests, migrations, generated folders, virtualenvs, and caches should stay
ignored. See `docs/structure-cohesion.md`.

The change-budget check prevents huge or overly diffuse changes from becoming a single opaque commit. It uses configured `source_roots` and `test_roots`, not hard-coded `src/` and `tests/`. Trivial package marker changes such as empty `__init__.py` additions are ignored because they do not add review complexity. In pre-commit, `--staged` limits diff-budget checks to the staged patch. Nonfatal warnings are shown in the aggregate verifier output; in `fresh-strict`, source changes without configured test-file changes fail in `precommit` unless explicitly allowed.

The suppression-budget check prevents broad `noqa`, `type: ignore`, `pylint: disable`, and `pragma: no cover` usage from hiding quality failures.

## Cleanup and dependency gates

deptry catches unused, missing, and transitive dependency problems.

vulture finds likely dead Python code.

Bandit scans Python source for common security issues. The verifier preserves
Bandit JSON as `.verify-logs/bandit.json` and prints compact findings instead
of dumping raw JSON into terminal output.

Semgrep provides local SAST in the `manual` profile when `enable_semgrep = true`.
Use local or pinned configs first, for example `semgrep.yml`, and keep
`--metrics=off` in committed args for private/local scans. The public package
extra installs Semgrep only on Python versions where its dependency graph is
currently resolver-friendly; Python 3.13 and newer users can still install
Semgrep separately when their platform supports it.

pip-audit checks Python packages for known vulnerabilities. It is disabled by default in this kit because it may use network access and, without an input file, can audit unrelated packages in the active environment. Enable it explicitly with pinned input, such as `pip_audit_args = ["-r", "config/dev-lock.txt"]`. In `fresh-strict`, enabling pip-audit without pinned args is a failure.

CycloneDX Python SBOM generation uses `cyclonedx-py` from `cyclonedx-bom`. It is disabled by default for drop-in repos, but this repository enables it in the `ci` profile so `.verify-logs/sbom.cdx.json` is uploaded with normal verification logs. For Python-only repositories, prefer this CycloneDX Python path over broader filesystem scanners.

License reporting and optional policy enforcement use `pip-licenses`. By default, `license_check_args = ["--from=mixed", "--format=json"]` generates `.verify-logs/licenses.json`. Add `--allow-only=...` or `--fail-on=...` to turn the same check into a blocking license policy once the repository has a real license policy. This repository enables the manual report but does not pretend a legal policy exists.

OSV Scanner is best reserved for repositories that genuinely need multi-ecosystem dependency CVE coverage. Configure `enable_osv_scanner = true` for those repositories; the default manual check writes `.verify-logs/osv-scanner.json`. Trivy is best reserved for repositories with Dockerfiles, container images, Kubernetes, Terraform, or other IaC assets. Configure `enable_trivy = true` for those repositories; the default manual check writes `.verify-logs/trivy.json`. Syft/Grype are better fits for broader deployable artifacts or container workflows. This repository intentionally keeps its own workflow Python-native and does not add Docker just to run those scanners.

## Docs Config Hygiene

Markdownlint-cli2 checks Markdown structure when `enable_markdownlint = true`.
It is treated as an external binary because it is a Node-backed tool, not a
Python dependency; this repository installs it through `npm ci` and
`package-lock.json`. YAML linting uses `yamllint` when `enable_yamllint = true`
and installs through `config/dev-lock.txt`. Taplo checks TOML formatting when
`enable_taplo = true`; it is also treated as a Node-backed external binary
installed by `npm ci`. Schema validation uses `check-jsonschema` when
`enable_check_jsonschema = true` and `check_jsonschema_args` declares a stable
schema contract. This repository enables GitHub Actions workflow schema
validation through `vendor.github-workflows`.

## Secret Scanning

Secret scanning is configured through `enable_secret_scanning`, `secret_scanner`,
`secret_scan_profiles`, and `secret_scan_history_profiles`. Gitleaks is the first
supported backend and is treated as an external binary. The abstraction is
backend-neutral so a future Betterleaks backend can be added without changing
the public config shape.

Normal scans run through `agent_maintainer.runners.secret_scan`: `full` scans the current
tree, `ci` scans the comparison range, and staged verifier runs scan the staged
diff through stdin. The manual `security` profile runs a full-history scan.
Gitleaks reports are written under `.verify-logs/` and run with redaction.

`config/dev-dependencies.txt` is the human-edited dependency input. `config/dev-lock.txt` is the pinned install and audit artifact when present; bootstrap and CI prefer it automatically.

## GitHub Actions policy

Workflows should declare least-privilege permissions, starting with
`permissions: contents: read` for verification-only jobs. This kit currently
uses trusted action version tags rather than full commit SHA pins, paired with
Dependabot `github-actions` updates so tag-pinned actions are reviewed
regularly. Revisit SHA pinning if the kit moves toward stricter supply-chain
requirements.

`actionlint` checks workflow syntax and common GitHub Actions mistakes when
`.github/workflows` exists. `zizmor` runs offline against workflows and
Dependabot config to catch risky CI/CD patterns. This repository enables both
through the normal full/CI verifier profiles.

## Configuration model

Shared path configuration is read from `[tool.agent_maintainer]` in `pyproject.toml`, then `AGENT_MAINTAINER_*` environment variables, then CLI flags. The important fields are:

```toml
[tool.agent_maintainer]
mode = "custom"
architecture_tool = "import-linter"
enable_interrogate = false
interrogate_fail_under = 80
source_roots = ["src"]
test_roots = ["tests"]
package_paths = ["src"]
coverage_source = ["src"]

[tool.agent_maintainer.diagnostics]
enabled = true
log_dir = ".verify-logs"
```

Mode can be `custom`, `legacy-ratchet`, or `fresh-strict`. Built-in defaults apply first, then mode defaults, then explicit pyproject fields, environment variables, and CLI flags.

Missing required roots fail in `precommit`, `full`, and `ci`; optional integrations are reported as skipped. In `fresh-strict` mode with `architecture_tool = "tach"`, `tach.toml` must exist, use `root_module = "forbid"`, explicitly assign each non-init Python source module under Tach's checked roots, and avoid module entries that no longer resolve to source files.

`doctor` checks that verifier diagnostics are coherent: logs exist, the manifest
is present and newer than the latest raw log, manifest-referenced logs and
artifacts still exist, `LAST_FAILURE.md` matches the pass/fail state of the
latest manifest, and the latest manifest does not reference disabled or removed
checks. It also checks the Codex hook audit trail when repo-local hooks are
enabled.
