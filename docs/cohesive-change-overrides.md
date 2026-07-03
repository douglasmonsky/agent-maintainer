<!-- docsync:object docs.cohesive_change_overrides.overview -->
# Cohesive-Change Overrides

Change budgets keep pull requests small by default. A cohesive-change override
is the rare exception for infrastructure migrations where splitting work would
create temporary dead code, fake boundaries, or incoherent intermediate states.

Use it only for cohesive maintenance work such as package migrations, hook
runtime rewrites, and architecture boundary moves. Do not use it for mixed
feature/refactor/docs/dependency bundles.

## Configuration

Overrides are disabled unless a repository explicitly enables them:

```toml
[tool.agent_maintainer]
cohesive_change_override_enabled = true
cohesive_change_override_paths = [
  "src/agent_maintainer/**",
  ".codex/hooks/**",
]
cohesive_change_override_max_lines = 2500
cohesive_change_override_max_files = 40
```

All changed Python source files must match `cohesive_change_override_paths`, and
the diff must stay within the configured maximum line and file counts.

## Required PR Explanation

CI only accepts an override when the pull request body contains this section:

```markdown
## Cohesive-Change Override

- Override requested: yes
- Why this is one cohesive unit:
- Why smaller PRs would make the repository less coherent:
- Tests/verification proving behavior is unchanged:
- Behavior change: none
```

Each field must contain useful text. The behavior field must state that behavior
is unchanged. If the section is missing, casual, empty, overbroad, or the diff
exceeds configured limits, the change-budget check still fails.

## Local Runs

Local runs cannot fully verify GitHub PR metadata. To test the path locally, set:

```bash
AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_REQUESTED=1 \
  python3 -m agent_maintainer verify --profile precommit
```

When accepted locally, the verifier emits a warning because GitHub CI must still
verify the required PR explanation before merge.
