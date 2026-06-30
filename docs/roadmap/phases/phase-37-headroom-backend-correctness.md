# Phase 37: Headroom Backend Correctness

## PR Title

```text
fix: align headroom compression adapter with message API
```

## Goal

Make the optional Headroom backend correct and explicitly experimental. The
adapter must pass sanitized supporting context as a message list, normalize
`CompressResult.messages`, and keep deterministic fallback behavior when
Headroom is missing or fails.

## Requirements

- Call Headroom with a `list[dict[str, Any]]` message payload rather than a raw
  string.
- Extract compressed text from returned messages when the result exposes a
  `messages` attribute or mapping key.
- Preserve existing string and mapping fallbacks only as compatibility paths.
- Keep sanitized supporting context as the only content passed to Headroom.
- Update docs to label Headroom optional and experimental until live integration
  has broader coverage.
- Add unit tests for message payload construction and `CompressResult.messages`
  normalization.

## Out Of Scope

- Do not make Headroom part of core dependencies.
- Do not require network credentials in normal verification.
- Do not change deterministic compression defaults.

## Acceptance Criteria

- Mocked Headroom adapter tests prove input shape and output normalization.
- Pack compression tests still prove fallback behavior.
- Precommit and focused context compression tests pass.

---
