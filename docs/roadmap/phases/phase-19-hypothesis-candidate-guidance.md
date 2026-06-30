# Phase 19: Hypothesis Candidate Guidance

## PR Title

```text
feat: suggest hypothesis property-test candidates
```

## Files

Update:

```text
src/agent_maintainer/test_intel/*
```

## Commands

```bash
python -m agent_maintainer test-intel hypothesis-candidates
python -m agent_maintainer test-intel hypothesis-candidates --changed
python -m agent_maintainer test-intel hypothesis-candidates --format json
```

## Candidate Rules

Rank functions higher when they are:

```text
typed
pure-ish
branchy
parsers
validators
normalizers
numeric/string boundary logic
recently changed
narrowly tested
```

## Output

```text
Hypothesis candidate:
  src/foo/score.py::normalize_score

Why:
  typed function
  branch complexity 7
  narrow current tests
  numeric boundary behavior

Suggested scaffold:
  @given(st.integers(min_value=0, max_value=100))
  def test_normalize_score_bounds(value):
      result = normalize_score(value)
      assert 0 <= result <= 1

Note: scaffold is a starting point, not a verified contract.
```

## Acceptance Criteria

- Candidate command works.
- No files are modified.
- Output is advisory.
- JSON output works.
- Precommit passes.

---
