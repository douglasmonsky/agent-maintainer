<!-- docsync:object docs.readme.overview -->
# Agent Maintainer

<p align="center">
  <img src="docs/assets/graphics/agent-maintainer-social-preview.png" alt="Make AI agents edit better. Agent Maintainer guides coding agents with maintainability checks, repair feedback, and workflow guardrails." width="900">
</p>

[![CI](https://github.com/douglasmonsky/agent-maintainer/actions/workflows/verify.yml/badge.svg)](https://github.com/douglasmonsky/agent-maintainer/actions/workflows/verify.yml)
[![PyPI](https://img.shields.io/pypi/v/agent-maintainer.svg)](https://pypi.org/project/agent-maintainer/)
![Python 3.11-3.14](https://img.shields.io/badge/python-3.11--3.14-blue)
[![License: MIT](https://img.shields.io/pypi/l/agent-maintainer.svg)](LICENSE)

Maintainability checks and repair-loop diagnostics for AI-assisted Python
repositories.

> Agent Maintainer is in beta. The core workflow is usable today, but starter
> files and defaults may change as it is tested across more Python repository
> layouts.

Agent Maintainer helps coding agents make smaller, safer, more reviewable code
changes. It wraps your existing quality tools in low-noise profiles, adds
change-budget and ratchet discipline, writes bounded diagnostics under
`.verify-logs`, and gives agents exact repair commands instead of dumping huge
logs into chat.

Read more where it matters:

- [Quick start](docs/quick-start.md)
- [First run walkthrough](docs/onboarding-first-run.md)
- [Diagnostics loop](docs/diagnostics-repair-loop.md)
- [Tool map](docs/tool-map.md)

## What It Is

Agent Maintainer is a repository maintenance control layer for AI-assisted
software development. It checks whether changes are small enough to review,
test-backed, type-checked, covered, diagnosable, and aligned with repository
structure.

It is strongest when an AI agent actively edits the repo: the agent gets a
compact pass/fail summary, run id, failed checks, and exact next commands while
raw evidence stays in run-scoped artifacts.

<!-- docsync:object.end docs.readme.overview -->
<!-- docsync:object docs.readme.quick_start -->
## Quick Start

Install the core toolset:

```bash
python -m pip install "agent-maintainer[core]"
```

Initialize a repo:

```bash
agent-maintainer init --track core --preset existing-app
```

Merge `config/pyproject.agent-maintainer.toml` into your `pyproject.toml`, tune
paths, then run:

```bash
agent-maintainer doctor
agent-maintainer verify --profile precommit
```

A healthy verification run is intentionally quiet:

```text
PASS
```

If it fails, read the bounded repair note first:

```bash
cat .verify-logs/LAST_FAILURE.md
```

The note links to run-scoped logs and gives exact expansion/rerun commands.

<!-- docsync:object.end docs.readme.quick_start -->
## Best First Experience: Try A Fresh Strict Repo

The clearest way to feel the value is to let an agent build something new under
strict settings before entropy starts.

```bash
python -m pip install "agent-maintainer[core]"
agent-maintainer init --track agent --preset strict-new-repo
```

Then ask your coding agent to build a small package, add tests, and finish by
running:

```bash
python3 -m agent_maintainer verify --profile precommit
```

The strict preset turns on the pressure that matters for AI-generated code:
small functions, covered behavior, low complexity, no broad suppressions,
architecture ownership, and test-backed source changes.

Deeper reads:

- [Fresh strict](docs/fresh-strict.md)
- [Agent hooks](docs/agent-client-hooks.md)
- [Generated guidance](docs/agent-maintainer-guidance.md)

<!-- docsync:object docs.readme.adoption_tracks -->
## Adoption Tracks

`init` separates files written from policy strictness. Each track uses generated
initializer templates so downstream repos receive the config, workflow, hook,
and metadata files for their adoption level without vendoring Agent Maintainer
source.

| Track | Best For | Writes |
|---|---|---|
| `core` | A minimum useful local CI maintenance loop. | Starter config, `config/dev-dependencies.txt`, pre-commit config, CI workflow. |
| `agent` | Repos where Codex, Claude Code, or other agents actively edit code. | Core plus `AGENTS.md`, generated guidance target, Codex hooks, Claude Code hooks. |
| `hardening` | Repos that want docs/config hygiene and security-adjacent surfaces too. | Agent plus Node-backed tooling metadata. |

Preview before writing:

```bash
agent-maintainer init --track agent --preset ai-agent-heavy --dry-run
```

Presets tune policy:

| Preset | Use When |
|---|---|
| `small-library` | A compact package should start with tighter budgets. |
| `existing-app` | An existing repo needs useful defaults without immediate strict-mode friction. |
| `ai-agent-heavy` | Agents frequently change code and source-only changes should fail. |
| `legacy-ratchet` | Existing debt should improve through ranked repair targets. |
| `strict-new-repo` | A clean repo can start with strict wemake and tighter budgets. |
| `team-small-python-lib` | A team-owned package wants small-library defaults. |
| `team-legacy-service` | A team-owned service needs legacy ratchets first. |
| `team-agent-heavy` | A team relies heavily on coding agents. |
| `team-security-sensitive` | A clean security-sensitive repo wants strict starter defaults. |

Read more:

- [Quick start](docs/quick-start.md)
- [Legacy ratchet](docs/legacy-ratchet.md)
- [Fresh strict](docs/fresh-strict.md)
- [Team policy templates](docs/team-policy-templates.md)
<!-- docsync:object.end docs.readme.adoption_tracks -->
<!-- docsync:object docs.readme.run_profiles -->
## Run Profiles

<p align="center">
  <img src="docs/assets/graphics/standard-runs-at-a-glance.png" alt="Agent Maintainer standard runs comparison showing fast, precommit, full, CI, security, and manual verification profiles." width="900">
</p>

| Profile | Purpose |
|---|---|
| `fast` | Hook-friendly edit feedback. |
| `precommit` | Local completion gate before finishing a task. |
| `full` | Deeper review gate before larger changes. |
| `ci` | GitHub Actions-equivalent verification with branch comparison. |
| `security` | Security-oriented scans, including history-oriented secret scanning when configured. |
| `manual` | Slow or intentionally heavy checks such as Mutmut and Semgrep. |

Canonical commands:

```bash
python3 -m agent_maintainer verify --profile precommit
python3 -m agent_maintainer verify --profile full
python3 -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
python3 -m agent_maintainer verify --profile security
python3 -m agent_maintainer verify --profile manual
```

Read more:
[tool map](docs/tool-map.md),
[diagnostics repair loop](docs/diagnostics-repair-loop.md),
[verification cadence](docs/agent-maintainer-guidance.md).

<!-- docsync:object.end docs.readme.run_profiles -->
<!-- docsync:object docs.readme.supported_checks -->
## Supported Checks And Scans

Agent Maintainer does not replace these tools. It coordinates them, gives them
stable profiles, captures artifacts, and turns failures into bounded repair
context.

| Area | Supported Checks |
|---|---|
| Change control | Change budget, staged diff checks, cohesive change plans, source-without-test-change policy. |
| Size and structure | File length budgets, folder cohesion hints, suppression budget, required layout checks. |
| Formatting and lint | Ruff format/check, Pylint, wemake-python-styleguide. |
| Types and tests | Pyright, pytest, pytest-cov, coverage, diff-cover. |
| Complexity | Radon reports, Xenon complexity gate. |
| Architecture | Tach, Import Linter, Archguard decision notes and impact tools. |
| Dependency hygiene | deptry, vulture. |
| Python security | Bandit, pip-audit. |
| Secrets | Gitleaks current-tree, staged/range, and history modes. |
| Ecosystems | Python core/reference provider; experimental configured-command TypeScript/JavaScript provider. |
| SAST | Semgrep in manual profile when enabled. |
| Multi-ecosystem CVEs | OSV Scanner when enabled. |
| Containers/IaC | Trivy when relevant to the repo. |
| SBOM and licenses | CycloneDX Python SBOM, pip-licenses. |
| GitHub Actions | actionlint, zizmor. |
| Docs/config hygiene | markdownlint-cli2, yamllint, Taplo, check-jsonschema. |
| Mutation testing | Mutmut target ratchet, result ratchets, advisory deep sweep executor. |
| Agent repair loop | `.verify-logs`, context commands, repair plans, PR summaries, static HTML reports. |

Read more:
[optional gates](docs/optional-gates.md),
[supported scans and agent use](docs/supported-scans-and-agent-use.md),
[ecosystem provider status](docs/provider-status.md),
[multi-ecosystem reviewability policy](docs/multi-ecosystem-reviewability-policy.md),

[mutation testing](docs/mutation-testing.md),
[architecture policy](docs/architecture-policy.md),
[test intelligence](docs/test-intelligence.md).

<!-- docsync:object.end docs.readme.supported_checks -->
## Ratcheting: Improve Existing Repos Without Freezing Them

Legacy repos usually cannot become strict overnight. Agent Maintainer separates
new regressions from old debt:

- changed-code coverage can block new untested work;
- suppression budget blocks new broad `noqa`, `type: ignore`, and coverage
  escapes;
- file-length and structure checks can warn before they block;
- ratchet commands rank the next repair targets;
- mutation target/result ratchets keep high-value mutation testing focused.

Useful commands:

```bash
python3 -m agent_maintainer ratchet status
python3 -m agent_maintainer ratchet next
python3 -m agent_maintainer events summary
python3 -m agent_maintainer events waste
python3 -m agent_maintainer wait github-run <run-id>
python3 -m agent_maintainer test-intel mutation-results
python3 -m agent_maintainer test-intel mutation-sweep
```

Read more:
[ratcheting](docs/ratcheting.md),
[mutation testing](docs/mutation-testing.md),
[cohesive change plans](docs/cohesive-change-plans.md).

<!-- docsync:object docs.readme.agent_loop -->
## How Agents Should Use It

For agent-heavy repos, install the `agent` track and commit the generated
guidance:

```bash
agent-maintainer init --track agent --preset ai-agent-heavy
python3 -m agent_maintainer guidance
```

Then agents should follow this loop:

1. Read `AGENTS.md` and `AGENTS.agent-maintainer.md`.
2. Make a small, coherent change.
3. Run focused tests while editing.
4. Let trusted Stop/SubagentStop hooks cover `precommit` for the final state.
   Run `python3 -m agent_maintainer verify --profile precommit` only when hooks
   are unavailable, bypassed, or a failure needs reproduction.
5. If verification fails, inspect `.verify-logs/LAST_FAILURE.md` and use the
   suggested `context` command instead of dumping raw logs.
6. For larger work, run one broad local profile before PR, usually `full`.
   Use `ci` instead when diff/base-ref, workflow, or profile behavior changed;
   run both only when that overlap is under test. Run `security` or `manual`
   when touching those gates, before release, or when explicitly requested.

Helpful repair commands:

```bash
python3 -m agent_maintainer context failures --limit 20
python3 -m agent_maintainer context log pyright --tail 120
python3 -m agent_maintainer repair-plan
python3 -m agent_maintainer report html
```

Read more:
[agent hooks](docs/agent-client-hooks.md),
[context safety](docs/context-safety.md),
[diagnostics repair loop](docs/diagnostics-repair-loop.md).

<!-- docsync:object.end docs.readme.agent_loop -->
## Trust Model

Agent Maintainer is designed to be safe to try:

- MIT licensed and open source.
- Package-first; downstream repos should not vendor `src/agent_maintainer`.
- Local-first verification; normal checks run against your repo and local tool
  outputs.
- Hooks no-op outside repos with `[tool.agent_maintainer]`.
- Output is bounded; raw logs live in `.verify-logs/runs/<run-id>/`.
- Secret scan artifacts are treated as sensitive/redacted diagnostics.
- CI uses least-privilege permissions and package-index publishing uses trusted
  publishing.
- This repo dogfoods strict settings, Python 3.11-3.14 compatibility, release
  checks, mutation ratchets, OSV, SBOM, licenses, docs/config hygiene, Codex
  hooks, and Claude Code hooks.

Read more:
[Release checklist](docs/release-checklist.md),
[troubleshooting](docs/troubleshooting.md),
[0.1.0b5 release notes](docs/releases/0.1.0b5.md).

## Configuration

Configuration can live in `pyproject.toml` or in a neutral Agent Maintainer
config file. Python repos should usually keep using `[tool.agent_maintainer]`
in `pyproject.toml`; mixed or future non-Python repos can use
`.agent-maintainer/config.toml` or `agent-maintainer.toml`.

```toml
[tool.agent_maintainer]
mode = "custom"
architecture_tool = "import-linter"
source_roots = ["src"]
test_roots = ["tests"]
package_paths = ["src"]
coverage_source = ["src"]
require_tests = true
coverage_fail_under = 80
diff_cover_fail_under = 90

[tool.agent_maintainer.diagnostics]
enabled = true
log_dir = ".verify-logs"
run_history_limit = 10
```

Precedence is built-in defaults, mode defaults, file config, environment
variables, then CLI flags. When multiple file configs exist,
`pyproject.toml` `[tool.agent_maintainer]` wins; otherwise
`.agent-maintainer/config.toml` wins over `agent-maintainer.toml`.
Environment overrides use the `AGENT_MAINTAINER_*` prefix.

```bash
AGENT_MAINTAINER_SOURCE_ROOTS=src,tests python3 -m agent_maintainer doctor
```

Read more:
[quick start](docs/quick-start.md),
[structure cohesion](docs/structure-cohesion.md),
[tool map](docs/tool-map.md).

## Setup Recommendations

Ask Agent Maintainer to inspect the repo before choosing a track and preset:

```bash
python3 -m agent_maintainer assess setup
python3 -m agent_maintainer assess setup --json
```

The advisor recommends `core`, `agent`, or `hardening`; a starting preset;
optional gates that match repository evidence; and follow-up prompts a coding
agent should answer before tightening config.

Read more:
[setup advisor](docs/setup-advisor.md).

## Reviewability Assessment

Inspect changed files by provider ecosystem and role without changing blocking
policy:

```bash
python3 -m agent_maintainer assess reviewability
python3 -m agent_maintainer assess reviewability --json
```

This is advisory. In the current beta, blocking reviewability gates remain
Python-backed while TypeScript/JavaScript policy adapters mature.

Read more:

[multi-ecosystem reviewability policy](docs/multi-ecosystem-reviewability-policy.md).

## File Baseline Assessment

Inspect simple file facts across configured file groups without changing
blocking verifier policy:

```bash
python3 -m agent_maintainer assess file-baselines
python3 -m agent_maintainer assess file-baselines --json
```

This is advisory. It works from explicit include/exclude globs and reports
matched files, changed files, changed lines, line-count findings, and compact
next commands. It is the broad filetype/path layer for docs, config, tests,
TSX, YAML, TOML, or other file groups; language-specific architecture still
belongs to provider adapters such as Tach for Python.

Read more:

[provider-neutral file baselines](docs/roadmap/provider-neutral-file-baselines.md).

<!-- docsync:object docs.readme.technical_debt -->
## Technical Debt Score

Generate an advisory maintenance-risk scorecard:

```bash
python3 -m agent_maintainer assess debt
python3 -m agent_maintainer assess debt --json
python3 -m agent_maintainer report html
```

The score is lower-is-better and decomposes into reviewability, tests/coverage,
type/style, architecture, dependencies/security, docs/config hygiene,
diagnostics, and ratchet/mutation maturity. It writes JSON and Markdown
artifacts under `.verify-logs` and appears in the verification summary and HTML
report when present.

Read more:
[Technical Debt Score](docs/technical-debt-score.md).

<!-- docsync:object.end docs.readme.technical_debt -->
## Install From Source

For local development on Agent Maintainer itself:

```bash
git clone https://github.com/douglasmonsky/agent-maintainer.git
cd agent-maintainer
python -m pip install -e ".[core]"
agent-maintainer --help
```

Normal downstream repositories should use the package-first init flow rather
than copying `src/agent_maintainer` into application source trees.

## Local Development

For this repo:

```bash
PYTHONPATH=src python3 -m agent_maintainer bootstrap
PYTHONPATH=src python3 -m agent_maintainer doctor --strict
PYTHONPATH=src python3 -m agent_maintainer verify --profile precommit
PYTHONPATH=src python3 -m agent_maintainer verify --profile full
```

Refresh the pinned dev lock after changing `config/dev-dependencies.txt`:

```bash
PYTHONPATH=src python3 -m agent_maintainer bootstrap
.venv/bin/python -m pip freeze --exclude-editable | sort > config/dev-lock.txt
```

Read more:
[Release checklist](docs/release-checklist.md),
[troubleshooting](docs/troubleshooting.md),
[roadmap](docs/ROADMAP.md).

## Further Reading

- [Changelog](CHANGELOG.md)
- [MIT License](LICENSE)
- [Context compression](docs/context-compression.md)
- [Cohesive change plans](docs/cohesive-change-plans.md)
- [Roadmap blueprint index](docs/roadmap/full-roadmap-blueprint.md)

Example starter projects:

- [Fresh-strict example](examples/fresh-strict)
- [Legacy-ratchet example](examples/legacy-ratchet)
- [Context-safe ratchet proof example](examples/context-safe-ratchet)
- [Cohesive change-plan proof example](examples/cohesive-change-plan)
- [Test-intelligence proof example](examples/test-intelligence)

Measured fixture case studies:

- [Split large legacy file](docs/case-studies/split-large-legacy-file.md)
- [Context-safe ratchet repair](docs/case-studies/context-safe-ratchet-repair.md)
