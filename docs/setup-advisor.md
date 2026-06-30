# Setup Advisor

The setup advisor inspects a repository and recommends a practical Agent
Maintainer starting point. It is local-only, deterministic, and advisory: it
does not write files or silently enable heavy gates.

## Commands

```bash
python3 -m agent_maintainer assess setup
python3 -m agent_maintainer assess setup --json
python3 -m agent_maintainer assess setup --target ../some-repo
```

Text output is meant for humans and coding agents. JSON output is meant for
automation and agent planning.

## What It Recommends

- `init --track`: `core`, `agent`, or `hardening`.
- `init --preset`: `strict-new-repo`, `existing-app`, `ai-agent-heavy`, or
  `legacy-ratchet`.
- Optional gates that match local repository evidence.
- Follow-up prompts for the coding agent before config is tightened.
- A confidence level based on how much evidence is available.

## Evidence Used

The advisor checks the local repository shape only:

- Python layout: `src`, flat packages, and test roots.
- Package metadata: `pyproject.toml`, dependency files, and locks.
- Local workflow files: GitHub Actions, pre-commit, and Git state.
- Agent surfaces: `AGENTS.md`, Codex hooks, and Claude Code hooks.
- Architecture files: `tach.toml` and `.importlinter`.
- Scanner-relevant assets: `package.json`, `go.mod`, Docker, IaC, YAML, TOML,
  and JSON files.

## Adoption Flow

Use the advisor before deciding how aggressively to initialize a repo:

```bash
python3 -m agent_maintainer assess setup
agent-maintainer init --track <recommended-track> --preset <recommended-preset> --dry-run
agent-maintainer init --track <recommended-track> --preset <recommended-preset>
agent-maintainer doctor
agent-maintainer verify --profile precommit
```

## Agent Prompt Use

The advisor emits prompts such as:

- Identify generated, vendored, migration, and fixture paths that checks should
  ignore.
- Map source modules into likely architecture boundaries before enabling strict
  Tach.
- List commands that already represent the repo's real test, lint, type, and
  build gates.

Those prompts are work instructions for a coding agent. Use them before
tightening thresholds on a mature repo.

## Relationship To Doctor

`doctor` answers: is the configured setup healthy?

`assess setup` answers: what setup should this repository probably adopt next?
