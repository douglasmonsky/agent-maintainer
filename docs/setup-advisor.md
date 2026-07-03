<!-- docsync:object docs.setup_advisor.overview -->
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
- Scanner-relevant assets: `package.json`, Docker, IaC, YAML, TOML,
  and JSON files.
- Root `package.json` script names, used only to suggest explicit
  TypeScript/JavaScript provider command mapping.

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

## TypeScript/JavaScript Advice

When a repository has `package.json` scripts such as `lint`, `typecheck`, or
`test`, the advisor may recommend enabling the experimental TypeScript provider.
That recommendation does not guess the package manager or invent commands.
Map existing scripts into explicit config, for example:

```toml
[tool.agent_maintainer]
enable_typescript = true
typescript_lint_command = ["npm", "run", "lint"]
typescript_typecheck_command = ["npm", "run", "typecheck"]
typescript_test_command = ["npm", "test"]
```

Keep TypeScript reviewability policy advisory until fixture or real-repo
evidence proves low-noise thresholds.

## Relationship To Doctor

`doctor` answers: is the configured setup healthy?

`assess setup` answers: what setup should this repository probably adopt next?
<!-- docsync:object.end docs.setup_advisor.overview -->
