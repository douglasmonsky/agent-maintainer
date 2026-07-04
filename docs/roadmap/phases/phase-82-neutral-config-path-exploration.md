# Phase 82: Neutral Config Path Exploration

## Status

Complete when this PR merges.

## Goal

Add an additive neutral config path for future non-Python and mixed repositories
without changing existing `pyproject.toml` behavior.

## Scope

- Keep `[tool.agent_maintainer]` in `pyproject.toml` as the highest-priority
  file-based configuration source.
- Add top-level neutral config loading from `.agent-maintainer/config.toml`.
- Add fallback top-level neutral config loading from `agent-maintainer.toml`.
- Keep environment variables and CLI flags overriding file config.
- Document precedence and add tests.

## Non-Goals

- No migration away from `pyproject.toml`.
- No provider-specific config schema.
- No new ecosystem support.
- No external plugin API.
- No generated starter-file changes in this phase.

## Acceptance Criteria

- Existing `[tool.agent_maintainer]` behavior remains unchanged.
- Neutral config works when `pyproject.toml` has no Agent Maintainer table.
- `.agent-maintainer/config.toml` wins over `agent-maintainer.toml`.
- Environment overrides still win over file config.
- Docs explain precedence.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m pytest tests/config/test_config_loading.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m agent_maintainer verify --profile precommit
```

Before merge, run one broad local profile by default; use CI-equivalent instead when diff/base-ref, workflow, or profile behavior changed. Run both only when that overlap is under test. Run security or manual when touching those gates, before release, or when explicitly requested.
