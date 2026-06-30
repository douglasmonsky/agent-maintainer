# Phase 44: Hook Output Invariant Tests

## PR Title

```text
test: enforce quiet hook output invariants
```

## Goal

Make the token budget behavior explicit and regression-tested: agent hooks should
be silent on success where the client allows silence, emit only required minimal
continue payloads for stop hooks, and keep failures bounded with artifact
pointers.

## Requirements

- Add tests for Codex and Claude Code hook success paths.
- Add tests proving failure output respects `context_hook_budget_chars`.
- Add tests proving full logs are not embedded in successful or bounded failure
  hook payloads.
- Document the invariant in hook docs.

## Acceptance Criteria

- Hook runtime tests pass.
- Precommit passes.
- Docs explain silent-success and bounded-failure behavior.

---
