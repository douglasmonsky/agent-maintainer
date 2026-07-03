# Architecture Decision: Agent Context Compression Boundary

Status: accepted

## What Changed?

Phase 119 moves reusable context compression primitives into
`agent_context.compression`:

- request/result models;
- deterministic `none`, `truncate`, and `extractive` backends;
- the optional Headroom adapter.

The previous product paths remain compatibility shims:

- `agent_maintainer.context.compression.models`
- `agent_maintainer.context.compression.backends`
- `agent_maintainer.context.compression.headroom`

## Why Necessary?

Compression request validation, deterministic compression, and Headroom result
normalization are reusable repair-loop primitives. They operate on already
sanitized context text and do not need Agent Maintainer config, verifier state,
hook runtime, or CLI orchestration.

Moving them into `agent_context` continues the internal-package extraction while
keeping product-specific context-pack assembly in `agent_maintainer.context`.

## Boundary

`agent_context.compression` owns:

- compression request/result dataclasses;
- backend names and backend dispatch;
- deterministic truncation/extractive behavior;
- optional Headroom loading and response normalization;
- backend error types.

`agent_maintainer.context` still owns:

- context-pack CLI flags and config lookup;
- context-pack compression orchestration across logs/files;
- fallback policy wiring for pack generation;
- context-pack builder and artifact writing;
- compatibility shims for previous import paths.

## Why This Is Not Architecture Drift

This is a narrow move from product namespace to an already-approved reusable
context package. It does not add a new public distribution, alter CLI/config
semantics, change hook output, or relax Tach rules.

## Alternatives Considered

1. Move all pack compression orchestration now. Rejected because pack
   orchestration still belongs near context-pack request wiring and CLI/config
   behavior.
2. Keep compression under `agent_maintainer.context`. Rejected because the
   lower-level backends are pure primitives and make the package boundary less
   clear when left in product namespace.
3. Remove compatibility shims. Rejected because shim cleanup should be a later
   explicit decision after the extraction sequence stabilizes.

## Review Or Expiration Condition

Revisit when context-pack compression orchestration can be moved without
introducing Agent Maintainer config or CLI dependencies into `agent_context`.
