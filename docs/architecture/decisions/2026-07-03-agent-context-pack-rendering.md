# Architecture Decision: Agent Context Pack Rendering Boundary

Status: accepted

## What Changed?

Phase 118 moves pure context-pack rendering and sanitizing helpers into the
`agent_context` internal package:

- `agent_context.pack_rendering`
- `agent_context.sanitize`

The previous product paths remain compatibility shims:

- `agent_maintainer.context.pack.rendering`
- `agent_maintainer.context.pack.sanitize`

## Why Necessary?

Context-pack rendering and deterministic redaction are reusable repair-loop
primitives. They do not need `MaintainerConfig`, verifier scheduling, ratchet
state, hook runtime, or CLI orchestration. Keeping them in
`agent_maintainer.context.pack` made the package boundary look more product
coupled than it actually is.

Moving only these pure helpers improves dependency direction without changing
user behavior or context-pack artifact shape.

## Boundary

`agent_context` now owns:

- Markdown and JSON context-pack rendering.
- Compact context-pack pointer rendering.
- Pack budget enforcement.
- Deterministic context text sanitizing.

`agent_maintainer.context` still owns:

- `agent-maintainer context ...` CLI commands.
- Context-pack build orchestration.
- Compression backend selection and Headroom integration.
- Ratchet target context.
- Compatibility shims for old internal import paths.

## Why This Is Not Architecture Drift

This is a narrow extraction from a product package into an already-approved
internal primitives package. It does not create a new public distribution,
change CLI behavior, change hook output, or relax architecture rules.

## Alternatives Considered

1. Move the whole context-pack builder now. Rejected because builder logic still
   depends on product-owned ratchet context, compression backend selection, and
   CLI-oriented request wiring.
2. Leave rendering in `agent_maintainer`. Rejected because it keeps pure
   rendering/redaction coupled to product orchestration and makes later
   extraction harder.
3. Remove compatibility shims immediately. Rejected because the current
   internal-package refactor is intentionally behavior-preserving and shim
   cleanup should be a separate decision.

## Review Or Expiration Condition

Revisit when context-pack builder and compression dependencies are isolated
enough to move safely, or when compatibility shims are reviewed for removal
after the internal package refactor stabilizes.
