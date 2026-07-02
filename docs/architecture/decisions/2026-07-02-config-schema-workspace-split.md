# 2026-07-02: Split Config Schema Support Modules

## Status

Accepted.

## Context

Phase 90 adds typed workspace configuration for future monorepo support.
`schema.py` was already close to the configured source-line limit, so adding
workspace fields there pushed the file over the strict budget.

## Decision

Keep `MaintainerConfig` in `schema.py`, but move cohesive supporting data into
small modules:

- `config.workspaces` owns `WorkspaceConfig`.
- `config.structure_defaults` owns structure-cohesion default path and hint
  constants.

`schema.py` imports and re-exports those names so existing callers can keep
using the current schema surface.

## Consequences

- The config schema stays below file-length limits.
- Workspace config has an obvious future home for helper behavior.
- Structure defaults are separated from the main config dataclass without
  changing runtime values.
- The Tach domain now explicitly models the new support modules.

## Alternatives Considered

- Increase the file-length threshold: rejected because this repo should
  dogfood the split pressure.
- Keep workspace data inside `schema.py`: rejected because it immediately
  exceeded the configured source-line cap.
- Move all config field metadata out of `schema.py`: deferred because this
  smaller split solves the current pressure with less churn.
