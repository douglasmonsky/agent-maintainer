# Context Estimate Runtime Assignment

## Status

Accepted.

## Context

Phase 10 adds `context estimate`, which estimates output size for files, logs,
and diffs before an agent expands large supporting context. The command is
orchestrated by `agent_maintainer.context.cli`, but the estimator itself reads
local files, resolves verifier log paths, and shells out to `git diff`.

## Decision

Assign `agent_maintainer.context.estimate` to the runtime layer in `tach.toml`.
The module depends on existing context log/failure helpers and local process
execution, so it is not a shared/domain primitive.

## Consequences

The CLI can call the estimator, while shared context primitives remain free of
filesystem and subprocess behavior. Future file-outline and context-pack
features should keep durable models in shared modules and local expansion logic
in runtime modules.
