# Safe File Context Command Runtime Assignment

## Status

Accepted.

## Context

Phase 11 completes the safe file context command after the primitive safety and
outline modules landed separately to stay within change-budget limits. The
command selects outlines, symbols, named symbol bodies, line ranges, and
around-line excerpts.

## Decision

Assign `agent_maintainer.context.files` to the runtime layer in `tach.toml`.
It coordinates file safety, Python outlines, and bounded rendering for local
file expansion. It is not a shared model module.

## Consequences

The CLI can expose bounded file context while preserving the rule that large or
unsafe files are never dumped by default. Future file expansion work should keep
new selectors behind `FileRequest` and run safety checks before reading content.
