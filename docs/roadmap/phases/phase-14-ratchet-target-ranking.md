# Phase 14: Ratchet Target Ranking

## PR Title

```text
feat: rank ratchet repair targets
```

## Files

Create:

```text
src/agent_maintainer/ratchet/ranking.py
src/agent_maintainer/ratchet/reporting.py
```

## Command

```bash
python -m agent_maintainer ratchet next
python -m agent_maintainer ratchet next --limit 5
python -m agent_maintainer ratchet next --format json
```

## Ranking Factors

Rank higher:

```text
new violation
worsened violation
changed in current diff
has failing tests nearby
has type/test failures nearby
already being edited
large but cohesive target
low blast radius
```

## Output

```text
Top ratchet targets:

1. src/legacy/big_service.py
   Why first: worsened file-length violation in current diff
   Current: 2,841 lines, threshold 600
   First command:
     python -m agent_maintainer context file src/legacy/big_service.py --outline
```

## Tests

Create:

```text
tests/ratchet/test_ranking.py
```

## Acceptance Criteria

- Default shows configured target count.
- Each target includes “why this target.”
- Each target includes first context command.
- JSON output works.
- Precommit passes.

---
