# Setup Advisor

The setup advisor is planned product work. Its job is to inspect a repository
before initialization and recommend a practical Agent Maintainer setup.

It should reduce the first-run decision burden without silently enabling heavy
tools.

## Goals

- Recommend an `init --track` value: `core`, `agent`, or `hardening`.
- Recommend an onboarding preset: `small-library`, `existing-app`,
  `ai-agent-heavy`, `legacy-ratchet`, or `strict-new-repo`.
- Identify optional gates that are relevant to the repo.
- Generate follow-up questions an AI agent should answer from local context.
- Emit both human-readable text and JSON.

## Evidence To Inspect

The first implementation should stay local and deterministic:

- Python layout: `src/`, flat package, `tests/`, scripts, notebooks.
- Package metadata: `pyproject.toml`, dependency files, lock files.
- Test tooling: pytest config, coverage config, existing CI test command.
- Existing quality tools: Ruff, Pyright, mypy, Pylint, pre-commit.
- Architecture files: `tach.toml`, `.importlinter`, package boundaries.
- CI/CD: GitHub Actions, Dependabot, release workflows.
- Agent surfaces: `AGENTS.md`, Codex hooks, Claude Code hooks.
- Security-relevant assets: Dockerfiles, IaC, Kubernetes, workflows, lock files.
- Docs/config assets: Markdown, YAML, TOML, JSON/YAML schemas.
- Legacy pressure: large files, broad suppressions, low coverage, missing tests.

## Suggested Interface

```bash
python3 -m agent_maintainer assess setup
python3 -m agent_maintainer assess setup --json
python3 -m agent_maintainer assess setup --target ../some-repo
```

The output should include:

- recommended install extra;
- recommended `init` command;
- recommended config adjustments;
- optional gates worth enabling now;
- optional gates to postpone;
- questions for a coding agent to answer before finalizing config;
- confidence level and missing evidence.

## Example Output Shape

```text
Recommended setup: agent + ai-agent-heavy
Confidence: medium

Why:
- Python package and tests detected.
- Existing GitHub Actions workflow detected.
- AGENTS.md absent; coding-agent hooks likely useful.
- No architecture contract detected; start with import-linter or Tach advisory.

Try:
agent-maintainer init --track agent --preset ai-agent-heavy --dry-run

Ask the agent:
- Which package paths should be covered by coverage_source?
- Are there generated folders that should be ignored?
- Should secret scanning run in full, ci, or security only?
```

## Non-Goals

- Do not mutate files by default.
- Do not enable slow/manual gates without explicit user action.
- Do not infer private security policy from file names alone.
- Do not call network services.
- Do not turn recommendations into pass/fail gates in the first version.

## Relationship To Doctor

`doctor` answers “is this configured setup healthy?”

The setup advisor should answer “what setup should this repository probably
adopt next?”
