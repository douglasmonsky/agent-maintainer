# Phase 29: PR / GitHub Actions Summary Report

## PR Title

```text
feat: write GitHub Actions summary report
```

## Output

```text
.verify-logs/pr-summary.md
```

## CI Integration

Append to:

```text
$GITHUB_STEP_SUMMARY
```

## Sections

```text
verification result
top failures
test intelligence
ratchet targets
change budget
change plan status
context pack path
expansion commands
```

## Acceptance Criteria

- Summary generated in CI.
- Summary bounded.
- Tests cover output.
- Precommit passes.

---
