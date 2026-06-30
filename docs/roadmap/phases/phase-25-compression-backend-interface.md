# Phase 25: Compression Backend Interface

## PR Title

```text
feat: add context compression backend interface
```

## Files

Create:

```text
src/agent_maintainer/context/compression.py
src/agent_maintainer/context/compression_backends.py
```

## Interface

```python
@dataclass(frozen=True)
class CompressionRequest:
    content: str
    content_kind: str
    target_chars: int
    preserve_terms: tuple[str, ...]
    forbidden_terms: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class CompressionResult:
    content: str
    backend: str
    original_chars: int
    compressed_chars: int
    exact_facts_preserved: bool
    warnings: tuple[str, ...] = ()
```

## Backends

Implement:

```text
none
truncate
extractive
```

## Preserve-Term Validation

If a backend drops a required preserve term, fall back to extractive compression.

## Acceptance Criteria

- Backends work.
- Preserve terms enforced.
- No Headroom dependency.
- Tests cover fallback.
- Precommit passes.

---
