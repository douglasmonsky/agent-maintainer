# Bounded Diff Context Runtime Assignment

## Status

Accepted.

## Context

Phase 12 adds bounded Git diff context for repair loops. Agents need summaries,
path lists, and path-specific patches without dumping arbitrarily large diffs.

## Decision

Assign `agent_maintainer.context.diff`,
`agent_maintainer.context.diff_git`, and
`agent_maintainer.context.diff_classify` to the runtime layer in `tach.toml`.
The modules shell out to local Git, parse changed paths and numstat output,
classify paths, and render bounded supporting context.

## Consequences

Diff expansion remains a local runtime concern. Shared context models stay free
of Git process execution, and future diff features should keep shown/omitted
counts and expansion commands in the output.
