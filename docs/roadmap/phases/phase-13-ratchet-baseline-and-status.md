# Phase 13: Ratchet Baseline and Status

## PR Title

```text
feat: add ratchet baseline and status model
```

## Files

Create:

```text
src/agent_maintainer/ratchet/__init__.py
src/agent_maintainer/ratchet/cli.py
src/agent_maintainer/ratchet/models.py
src/agent_maintainer/ratchet/baseline.py
src/agent_maintainer/ratchet/findings.py
src/agent_maintainer/ratchet/status.py
```

## Commands

```bash
python -m agent_maintainer ratchet status
python -m agent_maintainer ratchet baseline create
python -m agent_maintainer ratchet baseline refresh
python -m agent_maintainer ratchet explain
```

## Finding Model

```python
@dataclass(frozen=True)
class RatchetFinding:
    check: str
    identity: str
    path: str
    line: int | None
    severity: str
    metric: str | None
    value: int | float | str | None
    threshold: int | float | str | None
    message: str
    fingerprint: str
```

## Status Categories

```text
new
worsened
unchanged
improved
resolved
```

## Initial Checks

Implement for:

```text
file-length
structure-cohesion
```

## Baseline Provenance

Include:

```text
version
created_at
created_by
base_ref
repo_commit
dirty_state
mode
checks
notes
```

## Stale Detection

Detect:

```text
deleted files
dirty-generation baseline
base-ref mismatch
missing current violations
```

## Tests

Create:

```text
tests/ratchet/test_baseline.py
tests/ratchet/test_status.py
```

## Acceptance Criteria

- Baseline create/status works.
- New/worsened/improved/resolved works.
- Dirty-state provenance recorded.
- Basic stale detection works.
- Precommit passes.

---
