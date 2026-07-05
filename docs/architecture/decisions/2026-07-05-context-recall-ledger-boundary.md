# 2026-07-05: Context Recall Ledger Boundary

## Status

Accepted.

## Context

Phase 157 adds a compaction-safe recall ledger for high-value decisions,
constraints, artifact handles, tasks, summaries, and rehydrate commands. The
ledger should help agents resume work without depending on chat memory or
pasting raw logs into context.

## Decision

Add `agent_maintainer.context.recall` as a local JSONL-backed product module
owned by the context package. The context CLI owns `context ledger add` and
`context recall`; the ledger module owns validation, filtering, serialization,
and compact rendering.

The ledger stores only externalized facts supplied through explicit CLI fields.
It does not store hidden reasoning, call model APIs, use embeddings, or expand
large artifacts into agent-facing output.

## Consequences

- Recall survives thread compaction through `.verify-logs/context/ledger.jsonl`.
- Context recovery can point to artifact handles and rehydrate commands instead
  of large transcripts.
- Future context-pack work can read the ledger, but context-pack rendering
  remains separate from the ledger append/query primitive.
- Tach assigns `context.recall` explicitly so ledger ownership remains visible.
