# Phase 8: Smarter Source-Without-Test Guidance

## PR Title

```text
feat: use test intelligence in source-test change warnings
```

## Goal

Upgrade the source-without-test-change heuristic from a warning into actionable guidance.

## Files

Update:

```text
src/agent_maintainer/checks/change_budget.py
src/agent_maintainer/test_intel/*
```

## Behavior

Replace generic warning with:

```text
Source changed without likely relevant test changes.

Likely test files:
  tests/foo/test_bar.py
  tests/foo/test_baz.py

Run:
  python -m agent_maintainer test-intel changed --staged
```

If a test changed but it is not likely relevant:

```text
A test file changed, but no likely relevant test changed for the modified source.
```

## Rules

Do not make this more punitive yet.

Existing strict profile behavior remains unchanged.

## Tests

Add cases:

```text
source changed with no tests
source changed with relevant test
source changed with irrelevant test
staged mode
```

## Acceptance Criteria

- Warning includes likely tests.
- Existing fail/pass behavior preserved.
- Precommit passes.

---
