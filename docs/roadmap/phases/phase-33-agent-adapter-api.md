# Phase 33: Agent Adapter API

## PR Title

```text
refactor: add agent client adapter interface
```

## Interface

```python
class AgentClientAdapter(Protocol):
    name: str
    config_paths: tuple[str, ...]
    hook_paths: tuple[str, ...]

    def status(...) -> ...
    def install(...) -> ...
    def uninstall(...) -> ...
```

## Implement Adapters

```text
Codex
Claude Code
```

Do not add more agent clients in this phase.

## Acceptance Criteria

- Current behavior preserved.
- Tests pass.
- Precommit passes.

---
