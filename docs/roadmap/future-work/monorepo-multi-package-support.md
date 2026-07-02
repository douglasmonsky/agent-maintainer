# Future Work: Monorepo / Multi-Package Support

Status: promoted to
[`Phase 90: Workspace Config Foundation`](../phases/phase-90-workspace-config-foundation.md).

Phase 90 covers the typed config foundation. Later phases should wire
per-workspace coverage, ratchet targets, test intelligence, and shared root
policies.

## PR Title

```text
feat: add workspace config support
```

## Config

```toml
[tool.agent_maintainer.workspaces.api]
source_roots = ["services/api/src"]
test_roots = ["services/api/tests"]
coverage_source = ["services/api/src"]

[tool.agent_maintainer.workspaces.worker]
source_roots = ["services/worker/src"]
test_roots = ["services/worker/tests"]
coverage_source = ["services/worker/src"]
```

## Behavior

Support:

```text
per-workspace coverage
per-workspace ratchet targets
per-workspace test intelligence
shared root policies
```

## Acceptance Criteria

- Workspace config loads.
- Single-workspace behavior unchanged.
- Tests use multi-package fixture.
- Precommit passes.

---
