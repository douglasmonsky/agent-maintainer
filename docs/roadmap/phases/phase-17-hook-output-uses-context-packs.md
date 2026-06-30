# Phase 17: Hook Output Uses Context Packs

## PR Title

```text
feat: point hook failures to context packs
```

## Files

Update:

```text
src/agent_maintainer/hooks/runtime.py
src/agent_maintainer/context/packs.py
```

## Behavior

On hook failure:

```text
1. generate context pack when possible
2. emit compact failure pointer
3. include top one to three exact facts
4. include expansion commands
5. stay within hook budget
```

Example:

```text
Final verification failed.

Read:
  .verify-logs/context/PACK.md

Top finding:
  pyright: src/foo.py:88 incompatible type

Expand:
  python -m agent_maintainer context failures --check pyright --limit 20
```

## Tests

Update hook tests for:

```text
PostToolUse
Stop
SubagentStop
pack exists
pack generation fails
budget cap
```

## Acceptance Criteria

- Hooks do not dump large failure output.
- Hooks point to context pack.
- Hook audit remains compact.
- Precommit passes.

---
