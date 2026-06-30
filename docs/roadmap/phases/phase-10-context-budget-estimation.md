# Phase 10: Context Budget Estimation

## PR Title

```text
feat: estimate context expansion cost
```

## Goal

Estimate output size before expanding large context.

## Commands

```bash
python -m agent_maintainer context estimate
python -m agent_maintainer context estimate --file src/legacy/big.py
python -m agent_maintainer context estimate --log pyright --tail 500
python -m agent_maintainer context estimate --diff --summary
```

## Output

```text
Estimated output:
  chars: 41,200
  tokens: ~10,300
  default budget: 12,000 chars

Recommended:
  --tail 120
  --budget 50000 --confirm-large
```

Use:

```text
tokens ~= chars / 4
```

## Tests

Create:

```text
tests/context/test_estimate.py
```

## Acceptance Criteria

- Estimates logs, files, and diffs.
- Large expansion refusals use estimator.
- Precommit passes.

---
