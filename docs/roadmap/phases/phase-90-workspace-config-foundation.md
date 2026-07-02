# Phase 90: Workspace Config Foundation

Status: complete in PR.

## Goal

Begin monorepo and multi-package support by making workspace definitions a
typed, loaded configuration concept without changing existing single-repo
verification behavior.

## Scope

- Add a typed workspace config model.
- Load `[tool.agent_maintainer.workspaces.<name>]` tables from config files.
- Preserve existing top-level `source_roots`, `test_roots`, `package_paths`,
  and `coverage_source` behavior.
- Document that per-workspace coverage, ratchets, and test intelligence are
  future phases, not implied by this foundation.

## Non-Goals

- No per-workspace verifier scheduling yet.
- No per-workspace coverage gates yet.
- No per-workspace ratchet target ranking yet.
- No per-workspace test-intelligence routing yet.
- No generated starter config changes yet.
- No behavior change for repos without workspace config.

## Deliverables

- `MaintainerConfig.workspaces` typed field.
- Workspace TOML loading tests.
- Invalid workspace config error tests.
- Roadmap and future-work status updates.

## Acceptance Criteria

- Workspace config loads from `[tool.agent_maintainer.workspaces.<name>]`.
- Single-workspace and no-workspace behavior remains unchanged.
- Config metadata drift tests still pass.
- Existing verifier profiles still pass.

## Verification

Run:

```bash
python -m pytest tests/config/test_config_loading.py \
  tests/config/test_config_metadata.py -q
python -m agent_maintainer verify --profile precommit
```
