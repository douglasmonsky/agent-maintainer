# Safe File Context Primitive Runtime Assignment

## Status

Accepted.

## Context

Phase 11 starts with file safety and Python outline primitives used by safe
file context commands. The primitives inspect local paths, reject unsafe file
types, and parse Python source for navigation hints.

## Decision

Assign `agent_maintainer.context.file_safety` and
`agent_maintainer.context.python_outline` to the runtime layer in `tach.toml`.
These modules are context expansion helpers, not durable domain models. One
depends on local filesystem content; the other exists to support file expansion
rather than shared configuration or verification models.

## Consequences

The command layer can later orchestrate safe file context without letting raw
file IO leak into shared models. Future file context features should keep safety
checks ahead of rendering and should not add direct full-file dumping by
default.
