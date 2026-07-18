<!-- docsync:object docs.tool_map.overview -->
# Tool map

Experimental ecosystem providers are documented separately when they are not
part of the default Python workflow. See
[Experimental TypeScript/JavaScript Provider](typescript-javascript-provider.md)
for the first opt-in non-Python provider.

## Top-level command surface

| Category | Commands | Stability note |
| --- | --- | --- |
| Stable workflows | `doctor`, `guidance`, `init`, `install`, `verify`, `verify-plan`, `wait` | Quiet polling is stable; terminal rewake is experimental. |
| Repair and inspection | `assess`, `context`, `ratchet`, `repair-plan`, `test-intel` | Use these commands to inspect and plan repairs. |
| Optional local intelligence | `attention`, `events`, `report`, `scoring` | Local artifacts and datasets provide optional guidance. |
| Experimental integrations | `mcp` | Optional typed MCP tool surface. |
| Operations | `bootstrap`, `change-plan`, `hooks` | Checkout and workflow administration. |

<p align="center">
  <img src="assets/graphics/standard-runs-at-a-glance.png" alt="Agent Maintainer standard runs comparison showing typical fast full verification checks plus optional hardening profiles." width="900">
</p>

## Everyday gates

`python3 -m agent_maintainer` is the canonical entrypoint. Editable installs
also provide `agent-maintainer` for interactive use, but committed hooks and CI
should prefer the module command.

## Diff-aware verification planning

`python3 -m agent_maintainer verify-plan --base-ref origin/main` reports the
affected repository units, matched `.agent-maintainer/path-risk.toml` rules,
named evidence, review categories, configured checks, and canonical verifier
commands for a diff. Use `--staged` to inspect exactly what is staged, `--json`
for the deterministic schema-versioned report, and `--enforce` to return `1`
when required evidence is missing. Policy, configuration, and Git input errors
return `2`.

The planner is a repository-aware control layer, not a dynamic CI scheduler.
It never suppresses existing verifier gates, executes checks, or claims that an
unselected check is unnecessary. When the policy file exists, the optional
`verification-plan-policy` catalog check enforces it in the normal fast,
precommit, full, and CI profiles.

## Attention priority and provenance

`python3 -m agent_maintainer attention` accepts repeatable `--priority-path`
arguments for safe, user-requested tracked files that must be considered during
ledger sampling. Invalid, absolute, escaping, or sensitive paths are rejected;
safe paths outside the bounded tracked inventory are omitted and recorded in a
performance note.

Attention keeps changed, failed, exact-fact, and requested tracked paths ahead
of ordinary background sampling. The normal background budget is 5,000 files:
if required paths exceed it, all required paths are retained and the ledger
records an overflow performance note. Discovery and scoring still stop at the
hard 10,000-path ceiling.

Context attention entries identify their relevance as `direct`, `inferred`, or
`background`. Direct paths missing from an older otherwise-valid ledger report
a nullable `score: null` with empty components and a bounded explanation;
other ledger scores remain finite values from `0` to `1`. Background-only
entries never produce tight-hook risk notes.

Use `python3 -m agent_maintainer init --track core` for minimum package-first
adoption, `python3 -m agent_maintainer init --track agent` when Codex, Claude
Code, or other agents actively edit the repo, and `python3 -m agent_maintainer
init --track hardening` when optional docs/config hygiene files should also be
generated. Add `--preset small-library`, `--preset existing-app`, `--preset
ai-agent-heavy`, `--preset legacy-ratchet`, `--preset strict-new-repo`, or a
team preset such as `--preset team-agent-heavy` to tune starter policy without
changing which files the track writes.

Use `python3 -m agent_maintainer init --ci-only` when only the GitHub Actions
verification workflow and its Agent Maintainer dependency file are needed.

Use `python3 -m agent_maintainer assess setup` before first adoption to
recommend a track, preset, optional gates, and AI follow-up prompts. Use
`python3 -m agent_maintainer assess debt` to write an advisory lower-is-better
Technical Debt Score under `.verify-logs`; the static HTML report includes that
score when the artifact exists.

Use `python3 -m agent_maintainer bootstrap` for dependency-only local setup,
For package consumers, `bootstrap` operates on the current repository tree; it no longer falls back to the installed Agent Maintainer source checkout. When `config/dev-lock.txt` and `config/dev-dependencies.txt` are absent and the repository does not contain local `src/agent_maintainer`, bootstrap skips package dependency installation and leaves the consumer project package untouched. Use `python3 -m agent_maintainer doctor --root <repo> --format json` for scriptable setup checks outside the target repo CWD.
`python3 -m agent_maintainer doctor` for setup health, `python3 -m
agent_maintainer guidance` for generated agent-facing guidance, `python3 -m
agent_maintainer verify --profile precommit` for local completion checks,
`python3 -m agent_maintainer verify --profile full` for deeper review,
`python3 -m agent_maintainer verify --profile manual` for slow opt-in checks,
and `python3 -m agent_maintainer install` to explicitly install local pre-commit
and managed hooks without reinstalling dependencies. Both commands accept
`--dry-run`; bootstrap never installs hooks implicitly. Use `python3 -m
agent_maintainer hooks install all` to select managed agent-client hooks
directly. `hooks update` refreshes those files through the same lossless merge,
and `hooks uninstall` removes only manifest-owned entries and scripts.

When `.docsync/trace.yml` exists, Agent Maintainer adds a `docsync`
verification check to local profiles. The check runs `docsync check
--write-reports`, captures `.docsync/out/report.json`, and turns DocSync
findings into exact repair facts for context packs and repair capsules. Plain
standalone `docsync check` remains read-only.

`doctor --strict` turns setup warnings into a nonzero exit. Use it after bootstrap and after pushing local commits when you want a clean health signal that includes git sync state. In an Agent Maintainer source checkout, doctor verifies imports resolve local `src/agent_maintainer` and warns if the interactive `agent-maintainer` console script points at stale installed code; repair with `python -m pip install -e .`.

The `manual` profile is intentionally separate from `full`. Put slow, expensive, or artifact-producing checks there so normal local deep verification stays predictable. This repository also runs `.github/workflows/deep-verify.yml` on a weekly schedule and manual dispatch so the slow `security` and `manual` profiles are dogfooded without turning every pull request into a long-running release check.

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

Pyright enforces type discipline. The verifier runs it through a generated project config so `[tool.agent_maintainer].pyright_type_checking_mode` affects the actual Pyright invocation. Pyright JSON is also preserved as `.verify-logs/pyright.json` and listed in the verifier manifest. `pyright-strict-ratchet` is a separate manual-profile check: it runs strict Pyright, compares against `config/pyright-strict-baseline.json`, and fails only on configured regressions so repos can ratchet toward strict typing without making normal Pyright noisy.

Pytest and pytest-cov enforce behavior and coverage. The configured coverage
gate prevents untested new behavior from quietly entering the repository. The
verifier keeps root `coverage.xml`, run-scoped `coverage.json`, and
`pytest-junit.xml`; repair summaries use those artifacts to report test counts,
first failing tests, total coverage, and worst missing-line files without dumping
raw pytest output.

Mutmut provides mutation testing in the `manual` profile only. It is disabled by
default for drop-in use; enable it with `enable_mutmut = true` and configure
`mutmut_args` plus `[tool.mutmut]` source/test paths for nonstandard layouts.
`mutmut_target_min` is a cheap ratchet for repositories that want to prevent
the explicit `[tool.mutmut].only_mutate` target list from shrinking. When set
above zero, `full` and `ci` validate the target count and path-like target
existence without running mutation tests.
The verifier runs Mutmut through `agent_maintainer.runners.mutmut`, which removes the
generated `mutants` directory after successful runs. Set
`AGENT_MAINTAINER_KEEP_MUTANTS=true` only when explicitly debugging mutation
artifacts. Mutmut requires fork support, so native Windows users should run it
inside WSL.

For ratcheted Mutmut configs, Agent Maintainer also validates supported Mutmut
config keys plus concrete `also_copy` and `do_not_mutate` paths. This repo
dogfoods supported hardening knobs such as `max_stack_depth`, `also_copy`, and
explicit excluded wrapper files. Unsupported Mutmut keys are rejected rather
than silently ignored by the pinned Mutmut version.

When `[tool.agent_maintainer].mutmut_result_ratchet_enabled = true`, the Mutmut
runner exports `mutants/mutmut-cicd-stats.json` after a successful run and
fails the manual gate if configured survivor, suspicious, timeout, or score
budgets regress. Inspect the same stats with
`python -m agent_maintainer test-intel mutation-results`. When live `mutants/`
stats are cleaned, the command falls back to retained run or mutation-sweep
artifacts and prints the source path.

Use `python -m agent_maintainer test-intel mutation-sweep` to rank advisory
deep mutation sweep candidates by change, coverage, complexity, churn, and
ratchet signals. Planner mode does not run Mutmut. Add `--execute` to run
selected candidates in temporary copied worktrees and collect artifact-backed
stats without editing the source checkout. It suggests
`[tool.mutmut].only_mutate` promotions plus the manual verification command
for deliberate target expansion.

Verifier diagnostics write `.verify-logs/manifest.json` for machine-readable
run metadata and `.verify-logs/LAST_FAILURE.md` when the latest run fails.
`.verify-logs/pr-summary.md` is a bounded GitHub-friendly report with top
failures, test intelligence, ratchet targets, change-budget status,
change-plan status, context-pack path, and expansion commands.
`python3 -m agent_maintainer report html` turns those artifacts into a static
local `.verify-logs/report/index.html` report with links back to local logs,
coverage, architecture, release-readiness, and context-pack artifacts. CI
appends summary output to GitHub Actions and uploads safe verification logs.
Terminal output stays compact: pass/fail, profile, run id, duration with
expected profile hint, failed checks, exact expansion commands, and the
run-scoped log directory. Agents should use artifacts for raw stdout/stderr,
exit-code, threshold, log-path, and rerun context.
Structured repair summaries prefer safe artifacts for Ruff, Pyright, Bandit,
pytest/coverage, Semgrep, OSV Scanner, Gitleaks, and pip-audit. Secret scanner
summaries intentionally omit raw secret values and point to run-scoped artifacts
for details.
OSV Scanner v2 artifacts produce one exact fact per alias group. Fix versions
come only from OSV range events, valid relative lockfile paths remain available
as provenance, and unsafe machine paths are reduced to filename labels.
Managed agent-client hooks append local execution evidence to
`.verify-logs/hooks.jsonl`, and `doctor` reports latest audited hook status.
Hook install/update/status/uninstall behavior is routed through the shared
managed-file manifest and agent-client adapters. Current
adapters are Codex and Claude Code; they own client-specific config paths and
hook script paths, while the hook manager owns prompts, Git-private backups,
identity-aware merges/removals, and transactional writes/deletes.

`repair-plan` prints a non-mutating repair sequence for the next agent loop.
Use `python3 -m agent_maintainer repair-plan` for the latest failure,
`--ratchet` for the next ratchet target, `--check pyright` for one verifier
check, or `--target path/to/file.py` for one file. Markdown output is the
human/default format; `--format json` exists for automation. The command only
prints bounded guidance and context/test/verification commands; it does not edit
files, update baselines, or run checks.

`python3 -m agent_maintainer assess efficacy` summarizes local agent efficacy
signals from runtime-event JSONL and verifier manifests without reading raw chat
transcripts or raw check logs. Use it after dogfood sessions to inspect measured
duplicate-run avoidance, wait-helper success, context pointer follow-through,
repair-loop outcomes, first-failure-to-pass timing, and estimated repair-capsule
token savings. Metrics labeled `estimated` are artifact-backed proxies; metrics
labeled `unknown` need more explicit runtime events before they should drive a
ratchet.

## Maintainability gates

Radon reports cyclomatic complexity and maintainability metrics. Xenon converts complexity thresholds into a failing gate.

Pylint provides a backup for design smells, including module length through `max-module-lines`.

wemake-python-styleguide is an opt-in strictness gate for fresh repos and clean baselines. It runs only when `enable_wemake = true` or `AGENT_MAINTAINER_ENABLE_WEMAKE=1`, and the verifier requires the actual wemake plugin so plain flake8 cannot masquerade as the strict check.

Interrogate checks docstring coverage. It runs only when `enable_interrogate = true` or `AGENT_MAINTAINER_ENABLE_INTERROGATE=1`; use `interrogate_fail_under` as a ratchet floor rather than forcing a legacy repo to document every helper at once.

Tach and Import Linter are supported architecture boundary backends.
`architecture_tool = "import-linter"` is the backward-compatible default.
`architecture_tool = "tach"` runs Archguard Tach config check and then
`tach check --exact`.

This repository uses Tach for its own Agent Maintainer modules. Root
`tach.toml` stays short; package-level contracts live beside code in
`tach.domain.toml` files. In strict mode, the config check also requires each
non-init Python source file under Tach's checked roots to appear explicitly in a
Tach module entry, configured module entries to still resolve to source, every
module to declare `depends_on`, and broad `paths = [...]` buckets to stay below
the configured limit.

Archguard runs alongside Tach when `architecture_tool = "tach"`. Tach enforces the current architecture contract. Archguard governs changes to that contract. If `tach.toml` or `tach.domain.toml` changes, Archguard requires an architecture decision note in `docs/architecture/decisions/`. `archguard map`, `archguard impact <path>`, and `archguard explain-boundary <source> <target>` provide read-only ownership, dependency-direction, affected-test, boundary-violation, and decision-note context before editing architecture-sensitive files. They merge nested domain ownership with root rules, prefer explicit domain dependencies when present, and retain legacy layer direction for rules without an explicit allowlist. Affected-test hints are sorted and bounded. If root or nested policy cannot be loaded, Archguard reports the bounded load error and treats dependency direction as unknown rather than inferring an allowed boundary.

For the experimental provider, dependency-cruiser is the TypeScript/JavaScript
architecture-boundary counterpart to Tach. Configure an explicit
`typescript_dependency_cruiser_command` with cruise-result JSON output; Agent
Maintainer never invents dependency-cruiser rules, installs the tool, chooses a
package manager, or changes its exit status. Bounded facts use only
`summary.violations`. A five-million-character capture limit accommodates
real cruise graphs, and exit-zero findings surface as non-blocking warning
summaries. Nx boundaries remain a separate future adapter.

## Diff hygiene gates

The file-length check stops giant files. In `legacy-ratchet`, it can use `file_length_baseline` so old oversized files are tolerated only while they stay unchanged or improve; new and worsened oversized files fail.

`python3 -m agent_maintainer ratchet` records multi-check baselines under
`.agent-maintainer/ratchet-baseline.json` by default. Phase 13 supports
file-length and structure-cohesion findings, reporting `new`, `worsened`,
`unchanged`, `improved`, and `resolved` status plus stale-baseline signals.

The structure-cohesion check warns when one folder accumulates many Python files
and uses regex/layer hints to point at likely split candidates. It is advisory by
default and blocks only at the configured block threshold in `fresh-strict`.
Tests, migrations, generated folders, virtualenvs, and caches should stay
ignored. See `docs/structure-cohesion.md`.

The change-budget check prevents huge or overly diffuse changes from becoming a single opaque commit. It uses configured `source_roots` and `test_roots`, not hard-coded `src/` and `tests/`. Trivial package marker changes such as empty `__init__.py` additions are ignored because they do not add review complexity. In pre-commit, `--staged` limits diff-budget checks to the staged patch. Nonfatal warnings are shown in the aggregate verifier output; in `fresh-strict`, source changes without configured test-file changes fail in `precommit` unless explicitly allowed.

Cohesive-change overrides are a narrow legacy exception for large infrastructure migrations where smaller PRs would make the repository less coherent. Prefer explicit change plans for intentional large changes. Legacy overrides are disabled unless `cohesive_change_override_enabled = true`, require an allowlist of paths and maximum size, and require a filled `## Cohesive-Change Override` PR section before CI accepts the override. They cannot clear invalid, expired, or out-of-scope active change-plan failures.

The suppression-budget check prevents broad `noqa`, `type: ignore`, `pylint: disable`, and `pragma: no cover` usage from hiding quality failures.

## Cleanup and dependency gates

deptry catches unused, missing, and transitive dependency problems.

vulture finds likely dead Python code.

Bandit scans Python source for common security issues. The verifier preserves
Bandit JSON as `.verify-logs/bandit.json` and prints compact findings instead
of dumping raw JSON into terminal output.

Semgrep provides local SAST in the `manual` profile when `enable_semgrep = true`.
Use local or pinned configs first, for example `semgrep.yml`, and keep
`--metrics=off` in committed args for private/local scans. The `manual` and
`all` extras install Semgrep across the supported Python 3.11 through 3.14
matrix.

The optional npm-backed Markdown and TOML gates require Node.js 22 or newer.
Hardening initialization adds that engine contract to compatible package
metadata and reports an explicit conflicting Node engine for review instead of
silently installing incompatible tooling.

pip-audit checks Python packages for known vulnerabilities. It is disabled by default in this kit because it may use network access and, without an input file, can audit unrelated packages in the active environment. Enable it explicitly with pinned input, such as `pip_audit_args = ["-r", "config/dev-lock.txt"]`. When the input is a complete, pinned, transitive lockfile, add `--no-deps --disable-pip --progress-spinner off --timeout 20` to avoid slow resolver work without making ordinary PyPI latency fail the gate. Do not use that fast path for partial requirements files that still need dependency resolution. In `fresh-strict`, enabling pip-audit without pinned args is a failure.

CycloneDX Python SBOM generation uses `cyclonedx-py` from `cyclonedx-bom`. It is disabled by default for drop-in repos, but this repository enables it in the `ci` profile so `.verify-logs/sbom.cdx.json` is uploaded with normal verification logs. For Python-only repositories, prefer this CycloneDX Python path over broader filesystem scanners.

License reporting and optional policy enforcement use `pip-licenses`. By default, `license_check_args = ["--from=mixed", "--format=json"]` generates `.verify-logs/licenses.json`. Add `--allow-only=...` or `--fail-on=...` to turn the same check into a blocking license policy once the repository has a real license policy. This repository enables the manual report but does not pretend a legal policy exists.

OSV Scanner provides multi-ecosystem dependency CVE coverage. Configure `enable_osv_scanner = true`; the default manual check writes `.verify-logs/osv-scanner.json`. Its v2 artifact produces bounded exact repair facts grouped by advisory aliases, with fixes from OSV range events and only safe relative lockfile paths retained as targetable provenance. Unsafe machine paths are reduced to filename labels. This repository enables OSV as a dogfooded manual gate alongside its Python-native `pip-audit` gate. Trivy is best reserved for repositories with Dockerfiles, container images, Kubernetes, Terraform, or other IaC assets. Configure `enable_trivy = true` for those repositories; the default manual check writes `.verify-logs/trivy.json`. Syft/Grype are better fits for broader deployable artifacts or container workflows. This repository still does not add Docker or IaC just to run Trivy.

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
tree, `ci` scans the explicit `BASE_REF..HEAD` comparison range passed by the
verifier, and staged verifier runs scan the staged diff through stdin. The
manual `security` profile runs a full-history scan. Gitleaks reports are
written under `.verify-logs/` and run with redaction.

`config/dev-dependencies.in` is this repository's human-edited pip-compile
input. `config/dev-lock.txt` is the pinned install and audit artifact; bootstrap
and CI prefer it automatically. Generated consumer projects may still use the
standalone `config/dev-dependencies.txt` bootstrap input.

## GitHub Actions policy

Workflows should declare least-privilege permissions, starting with
`permissions: contents: read` for verification-only jobs. This kit currently
uses trusted action version tags rather than full commit SHA pins, paired with
Dependabot `github-actions` updates so tag-pinned actions are reviewed
regularly. Revisit SHA pinning if the kit moves toward stricter supply-chain
requirements.

`actionlint` checks workflow syntax and common GitHub Actions mistakes when
`.github/workflows` exists. `zizmor` runs offline against workflow files to
catch risky CI/CD patterns; Dependabot configuration is validated separately.
This repository enables both through the normal full/CI verifier profiles.

## Configuration model

Shared path configuration is read from `[tool.agent_maintainer]` in
`pyproject.toml` when present. If that table is absent, Agent Maintainer reads
the first neutral config file found: `.agent-maintainer/config.toml`, then
`agent-maintainer.toml`. `AGENT_MAINTAINER_*` environment variables and CLI
flags override file config. The important fields are:

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

Mode can be `custom`, `legacy-ratchet`, or `fresh-strict`. Built-in defaults
apply first, then mode defaults, file config, environment variables, and CLI
flags. Config-field metadata guards this public surface against schema/env/CLI
drift; see [Configuration Metadata](config-metadata.md).

`doctor` reports unknown `[tool.agent_maintainer]` and
`[tool.agent_maintainer.diagnostics]` keys as warnings so typoed policy does
not silently disappear. `doctor --strict` turns those warnings into a nonzero
setup result through normal strict status behavior.

Path and profile CLI options still accept comma-separated values. Tool
passthrough options preserve each repeated flag exactly; pass separate tool
arguments by repeating the option instead of relying on comma splitting:

```bash
python3 -m agent_maintainer verify --semgrep-arg scan --semgrep-arg --config=semgrep.yml,local
```

Missing required roots fail in `precommit`, `full`, and `ci`; optional integrations are reported as skipped. In `fresh-strict` mode with `architecture_tool = "tach"`, `tach.toml` must exist, use `root_module = "forbid"`, explicitly assign each non-init Python source module under Tach's checked roots, and avoid module entries that no longer resolve to source files.

`doctor` checks verifier diagnostics coherence: logs exist, the manifest is
newer than the latest raw log, manifest-referenced log artifacts still exist,
`LAST_FAILURE.md` matches the latest manifest pass/fail state, and the latest
manifest does not reference disabled or removed checks. It also warns about
generated duplicate names such as `* 2*` and `* copy*`; inspect those files
before deleting them. It also checks the agent hook audit trail when repo-local
hooks are enabled.
<!-- docsync:object.end docs.tool_map.overview -->
