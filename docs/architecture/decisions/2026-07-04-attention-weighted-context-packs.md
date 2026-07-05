# 2026-07-04: Attention-weighted context packs

## Status

Accepted.

## Context

The attention ledger introduced a deterministic local score for files that are
likely to matter to future agent calls. Context packs are the main bounded
context surface agents use after verifier failures, so they should be able to
carry those scores without expanding raw log or file excerpts.

## Decision

Add a product-layer adapter in `agent_maintainer.context.pack.attention` that
reads `.verify-logs/attention/files.json` and builds an optional `attention`
payload block for context packs. The adapter may attach attention metadata to
exact repair facts and choose compact fallback entries from selected log text.

Reusable rendering in `agent_context.pack_rendering` remains generic: it renders
the optional `attention` payload if present, but it does not import Agent
Maintainer product modules or read ledger files directly.

`src/agent_context/tach.domain.toml` adds `attention_rendering` as a small
sibling renderer so `pack_rendering` stays under configured member-count
limits. `src/agent_maintainer/context/tach.domain.toml` adds `pack.attention`
as the product-side adapter boundary.

## Consequences

Hook-safe context-pack pointers can show a few compact risk notes without
pasting extra raw context. Existing context-pack keys and default context budget
remain unchanged, and packs still work when no ledger exists.
