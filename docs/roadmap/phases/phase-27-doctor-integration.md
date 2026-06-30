# Phase 27: Doctor Integration

## PR Title

```text
feat: report context ratchet and change-plan health in doctor
```

## Doctor Rows

Add:

```text
context config
context budgets
large-file outline
context pack directory
context pack upload safety
ratchet baseline
ratchet guidance
change plans
compression backend
Headroom backend
test intelligence artifacts
```

## States

Use:

```text
active
disabled
not applicable
missing
unsafe config
```

## Acceptance Criteria

- JSON doctor output stable.
- Missing Headroom not failure unless enabled.
- Invalid change plans detected.
- Stale ratchet guidance detected.
- Unsafe context pack upload detected.
- Tests added.
- Precommit passes.

---
