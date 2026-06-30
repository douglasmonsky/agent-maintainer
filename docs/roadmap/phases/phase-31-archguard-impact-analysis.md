# Phase 31: Archguard Impact Analysis

## PR Title

```text
feat: add archguard architecture impact commands
```

## Commands

```bash
archguard map
archguard impact src/foo.py
archguard explain-boundary src/a.py src/b.py
```

## Output

```text
module ownership
dependency direction
changed modules
affected tests
boundary violations
decision notes
```

## Acceptance Criteria

- Commands work on this repo.
- Tests cover Tach fixtures.
- Precommit passes.

---
