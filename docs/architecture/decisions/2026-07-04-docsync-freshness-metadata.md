# DocSync Freshness Metadata Boundary

## Status

Accepted.

## Context

DocSync now needs passive freshness metadata for documentation objects and
evidence anchors. The metadata should be generated state, not prose that agents
or maintainers manually edit, and it should reuse the resolved DocSync index
rather than introducing another scanner path.

## Decision

Add `docsync.freshness` as a DocSync-internal reporting module. The module may
depend on `docsync.core.models` because it renders freshness state from the
resolved `DocSyncIndex`. `docsync.commands.core` may depend on
`docsync.freshness` to expose the `docsync freshness` command.

The module does not depend on `agent_maintainer` or `archguard`, preserving the
DocSync extraction boundary.

## Consequences

- Freshness state lives in `.docsync/out/freshness.json`.
- Normal DocSync checks remain unchanged.
- Future verifier integration can consume the generated state without making
  human documentation carry manual timestamps.

## Alternatives Considered

- Add freshness rendering directly to `docsync.commands.core`. Rejected because
  command handlers should stay orchestration-focused.
- Add freshness fields to human Markdown documents. Rejected because it would
  create noisy documentation diffs and invite agents to manually edit generated
  timestamps.
