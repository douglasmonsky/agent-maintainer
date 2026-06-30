# Phase 63: Configured-Repo-Only Codex and Claude Hooks

## PR Title

```text
test: cover configured-repo hook opt-in
```

## Scope

Confirm global or user-level agent hooks remain safe: the runtime must no-op
outside repositories that explicitly contain `[tool.agent_maintainer]`.
Existing runtime tests cover Codex and Claude Code no-op behavior; add direct
tests around the opt-in predicate so the boundary is clear.

## File Targets

```text
src/agent_maintainer/hooks/runtime.py
tests/hooks/test_hook_opt_in.py
tests/hooks/test_hook_runtime.py
docs/ROADMAP.md
```

## Requirements

- Hooks may be installed globally, but execution must be repo-configured.
- Repositories without `pyproject.toml` or without `[tool.agent_maintainer]`
  must not run verifier commands.
- Codex and Claude Code no-op tests stay explicit.

## Acceptance Criteria

- Focused tests cover unconfigured repo no-op behavior and opt-in detection.
- Precommit, full, ci, security, manual profiles pass before PR merge.
