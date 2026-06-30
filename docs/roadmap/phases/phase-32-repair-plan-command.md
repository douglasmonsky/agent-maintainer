# Phase 32: Repair Plan Command

## PR Title

```text
feat: add non-mutating repair plan command
```

## Commands

```bash
agent-maintainer repair-plan
agent-maintainer repair-plan --ratchet
agent-maintainer repair-plan --check pyright
agent-maintainer repair-plan --target src/legacy/big_service.py
```

## Output

Markdown repair plan:

```text
objective
current target
recommended sequence
context commands
test commands
verification commands
stop conditions
```

## Rule

This command never edits files.

## Acceptance Criteria

- Output bounded.
- JSON output exists.
- Tests cover ratchet/check/target modes.
- Precommit passes.

---
