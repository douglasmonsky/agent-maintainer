# Hook Runtime Context Pack Boundary

## Status

Accepted.

## Context

Phase 17 changes hook failure output from raw verifier stdout/stderr snippets to
bounded context-pack pointers. The shared hook runtime now coordinates verifier
execution, hook audit records, bounded context-pack failure context, and
client-specific block responses.

## Decision

Move `agent_maintainer.hooks.runtime` from the Tach runtime layer to the
orchestration layer. Add `agent_maintainer.hooks.context` to the orchestration
layer.

The runtime module composes lower-level hook audit helpers, verifier execution,
and hook-context construction. The hook-context helper composes configuration
loading, context-pack generation, pack-pointer rendering, and fallback
truncation. That is orchestration work rather than a single low-level runtime
primitive.

## Alternatives Considered

- Invoke `context pack` through a subprocess from the runtime layer: rejected
  because it would hide an internal dependency behind process execution and make
  failure handling harder to test.
- Keep `hooks.runtime` in the runtime layer and duplicate pack-pointer logic:
  rejected because it would split context-pack behavior across two modules.

## Still Forbidden

Hook wrappers under `.codex/hooks` and `.claude/hooks` should remain thin
entrypoints. Low-level hook audit helpers should not import context pack
generation. Context pack generation may be orchestrated by hook modules, but
file/log/diff safety rules remain in the context package.
