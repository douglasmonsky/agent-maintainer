# 2026-07-06: Attention signal context boundary

## Status

Accepted.

## Context

Phase 163 added performance guards to attention-ledger signal collection:
tracked repository files are collected once per ledger build, large local
artifacts are read with a byte cap, and guard notes are written into ledger
inputs. Keeping that state in `agent_maintainer.attention.signals` pushed the
module over the style member limit and mixed shared per-build context with the
signal extractors.

## Decision

Add `agent_maintainer.attention.signal_context` as a small internal module that
owns attention signal defaults and the per-build `AttentionSignalContext`.
`builder` constructs the context using `signals.tracked_files`, and `signals`
consumes the context while continuing to own deterministic artifact and path
signal extraction.

## Consequences

The attention package keeps one bounded file-list scan per ledger build without
making `signals` a context/state module. The Tach domain contract now records
`builder -> signal_context` and `signals -> signal_context`; no other package
boundary changes.

## What remains forbidden?

`signal_context` must stay local and deterministic. It must not read verifier
logs, DocSync artifacts, runtime events, Git history, network resources, or own
attention score policy. Those responsibilities remain in `signals` and
`builder`.

## Review or expiration condition

Revisit if attention scoring gains another shared per-build state object or if
the context grows beyond bounded file tracking and artifact-read limits.
