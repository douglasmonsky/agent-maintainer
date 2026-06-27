# Agent Maintainer

Maintainability checks and repair-loop diagnostics for AI-assisted Python repositories.

Agent Maintainer helps Python repositories stay maintainable under AI-assisted
development. It combines low-noise verification, change budgets, suppression
controls, coverage gates, type checks, architecture checks, security checks, and
structured diagnostics into one workflow for humans and coding agents.

## What This Is

Agent Maintainer is a repository maintenance control layer for AI-assisted code
changes. It checks whether changes are small enough to review, test-backed,
type-checked, covered, diagnosable, and aligned with repo structure.

## What This Is Not

Agent Maintainer is not a runtime AI safety guardrail system. It does not
moderate model outputs, filter prompts, block jailbreaks, or validate chatbot
responses. It focuses on repository health during AI-assisted software
development.

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
verification fails, inspect the generated diagnostics before changing
thresholds or suppressions:

```bash
cat .verify-logs/LAST_FAILURE.md
```

The failure note includes failed checks, relevant artifact paths, and an exact
rerun command.

The console command is convenient for local use. Committed automation should use
the module entrypoint because it works reliably in editable and local-source
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
| Required repo layout | verifier layout checks |
| Style and simple defects | Ruff |
| Type discipline | Pyright |
| Tests and total coverage | Pytest, pytest-cov, coverage |
| Changed-code coverage | diff-cover |
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
day one. `mode = "legacy-ratchet"` is for existing repositories where heavy
gates should remain opt-in while changed-code discipline ramps up. This repo
self-enforces stricter settings than the starter template, including 90 percent
total coverage.

Environment overrides use the `AGENT_MAINTAINER_*` prefix, for example:

```bash
AGENT_MAINTAINER_SOURCE_ROOTS=src,tests python3 -m agent_maintainer doctor
```

## Agent Guidance

The generated sidecar gives coding agents the current repo policy without
copying long instructions into every prompt:

```bash
python3 -m agent_maintainer guidance
python3 -m agent_maintainer guidance --check
```

It writes `AGENTS.agent-maintainer.md` from `[tool.agent_maintainer]`. Update
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

## Legacy Vendored Install

Package-first adoption is preferred. Vendoring the tool source into another
repository is now an advanced private-fork option for early experimentation.
If you vendor it, keep the generated config and docs aligned with the installed
package model and do not copy `src/agent_maintainer` into normal application
source trees.

## Why Not Call This Guardrails?

In AI tooling, "guardrails" usually means runtime model safety controls. Agent
Maintainer is different: it focuses on repository maintenance during
AI-assisted software development. It helps coding agents and humans keep changes
reviewable, tested, and diagnosable.

## Further Reading

- `docs/tool-map.md` maps profiles to tools.
- `docs/fresh-strict.md` explains strict new-repo adoption.
- `docs/legacy-ratchet.md` explains incremental adoption for existing repos.
- `docs/codex-hooks.md` documents Codex hook setup and trust behavior.
- `docs/release-checklist.md` lists beta release packaging checks.
- `docs/troubleshooting.md` covers common setup failures.
- `docs/structure-cohesion.md` explains folder-size and cohesion hints.
