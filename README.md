# Agent Maintainer

Maintainability checks and repair-loop diagnostics for AI-assisted Python
repositories.

> Agent Maintainer is in beta. The core workflow is usable, but starter files
> and defaults may change as it is tested across more Python repository layouts.

Agent Maintainer helps Python repositories stay maintainable under AI-assisted
development. It combines low-noise verification, change budgets, suppression
controls, coverage gates, type checks, architecture checks, security checks, and
structured diagnostics into one workflow for humans and coding agents.

## What This Is

Agent Maintainer is a repository maintenance control layer for AI-assisted code
changes. It checks whether changes are small enough to review, test-backed,
type-checked, covered, diagnosable, and aligned with repo structure.

## What This Is Not

Agent Maintainer is not a runtime AI safety system. It does not moderate model
outputs, filter prompts, block jailbreaks, or validate chatbot responses. It is
also not a prompt/output moderation framework. Agent Maintainer focuses on
repository health during AI-assisted software development.

## Quick Start

Install the core toolset:

```bash
python -m pip install "agent-maintainer[core]"
```

Initialize a repository:

```bash
agent-maintainer init --track core
```

Merge `config/pyproject.agent-maintainer.toml` into your `pyproject.toml`, tune
paths for your repo, then check setup health:

```bash
agent-maintainer doctor
agent-maintainer verify --profile precommit
```

## First Successful Run

Healthy setup output should be quiet:

```text
PASS
```

`doctor` prints one compact `PASS`, `WARN`, or `FAIL` row per setup check. If
verification fails, inspect generated diagnostics before changing thresholds or
suppressions:

```bash
cat .verify-logs/LAST_FAILURE.md
```

The failure note includes failed checks, relevant artifact paths, and an exact
rerun command.

The console command is convenient for local use. Committed automation should use
the module entrypoint because it works reliably in editable local-source
contexts:

```bash
python3 -m agent_maintainer verify --profile precommit
```

## Adoption Tracks

`init` writes starter files for three adoption levels:

| Track | Use When | Writes |
|---|---|---|
| `core` | You want the minimum useful maintenance loop. | Starter config, `config/dev-dependencies.txt`, pre-commit config, CI workflow. |
| `agent` | Coding agents actively edit the repo. | Core files plus `AGENTS.md` and Codex hook files. |
| `hardening` | You want docs/config hygiene and security-adjacent surfaces. | Agent files plus Node-backed tooling metadata. |

Preview writes before changing a repo:

```bash
python3 -m agent_maintainer init --track agent --dry-run
```

Existing files are not overwritten unless `--force` is passed.

## Common Commands

```bash
python3 -m agent_maintainer bootstrap
python3 -m agent_maintainer doctor --strict
python3 -m agent_maintainer guidance
python3 -m agent_maintainer guidance --check
python3 -m agent_maintainer verify --profile fast
python3 -m agent_maintainer verify --profile precommit
python3 -m agent_maintainer verify --profile full
python3 -m agent_maintainer verify --profile ci
python3 -m agent_maintainer verify --profile security
python3 -m agent_maintainer verify --profile manual
```

Profiles are intentionally stable:

| Profile | Purpose |
|---|---|
| `fast` | Hook-friendly checks after edits. |
| `precommit` | Local completion gate. |
| `full` | Deeper review gate before larger merges. |
| `ci` | GitHub Actions gate. |
| `security` | Security-oriented scan profile. |
| `manual` | Slow opt-in tools such as mutation testing and Semgrep. |

## What The Tool Checks

| Concern | Enforcement |
|---|---|
| Oversized Python files | `agent_maintainer.checks.file_lengths` |
| Huge or diffuse changes | `agent_maintainer.checks.change_budget` |
| Broad suppressions | `agent_maintainer.checks.suppression_budget` |
| Required repo layout | Verifier layout checks |
| Style and simple defects | Ruff |
| Type discipline | Pyright |
| Test coverage | Pytest, pytest-cov, coverage, diff-cover |
| Complexity | Radon reports and Xenon gate |
| Architecture boundaries | Tach or Import Linter |
| Dependency hygiene | deptry |
| Dead code | vulture |
| Security checks | Bandit, pip-audit, Gitleaks, Semgrep when enabled |
| Supply-chain artifacts | CycloneDX Python SBOM and pip-licenses when enabled |
| GitHub Actions checks | actionlint and zizmor when workflows exist |
| Docs/config hygiene | markdownlint-cli2, yamllint, Taplo, check-jsonschema when enabled |
| Agent feedback | `AGENTS.agent-maintainer.md` and `.verify-logs` diagnostics |

## Configuration

Configuration lives in `pyproject.toml`:

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
```

`mode = "fresh-strict"` is for new repositories that can block strict checks on
day one. `mode = "legacy-ratchet"` is for existing repositories where heavier
gates should remain opt-in while changed-code discipline ramps up. This
repository self-enforces stricter settings than the starter template, including
90 percent total coverage.

Environment overrides use the `AGENT_MAINTAINER_*` prefix:

```bash
AGENT_MAINTAINER_SOURCE_ROOTS=src,tests python3 -m agent_maintainer doctor
```

## Agent Guidance

The generated sidecar gives coding agents current repo policy without copying
long instructions into every prompt:

```bash
python3 -m agent_maintainer guidance
python3 -m agent_maintainer guidance --check
```

This writes `AGENTS.agent-maintainer.md` from `[tool.agent_maintainer]`. Update
configuration first, then regenerate the sidecar.

## Optional Tooling

Install extras by adoption level:

```bash
python -m pip install "agent-maintainer[core]"
python -m pip install "agent-maintainer[hardening]"
python -m pip install "agent-maintainer[manual]"
python -m pip install "agent-maintainer[all]"
```

Node-backed tools such as `markdownlint-cli2` and Taplo are managed through
`package.json` when a repo opts into the hardening track:

```bash
npm ci
```

## Install From Source

For local development on Agent Maintainer itself, clone the repository and run:

```bash
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

## Further Reading

- [MIT License](LICENSE)
- [Changelog](CHANGELOG.md)
- [Tool map](docs/tool-map.md)
- [Fresh-strict mode](docs/fresh-strict.md)
- [Legacy-ratchet mode](docs/legacy-ratchet.md)
- [Codex hooks](docs/codex-hooks.md)
- [Release checklist](docs/release-checklist.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Structure cohesion](docs/structure-cohesion.md)
