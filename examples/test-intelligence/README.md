# Test Intelligence Example

This example shows how changed-source mapping and advisory test-intelligence
commands help an agent pick focused tests before running broader profiles.

## Run

From this directory, with Agent Maintainer installed:

```bash
git init
git add .
git commit -m "example baseline"
agent-maintainer test-intel changed --base-ref HEAD
agent-maintainer test-intel hypothesis-candidates --changed --base-ref HEAD
agent-maintainer test-intel crosshair-candidates --format json
agent-maintainer verify --profile precommit --base-ref HEAD
```

## Intentional Failure

`src/scoring/rubric.py` does not clamp scores above the maximum. The repair flow
should identify `tests/test_rubric.py` as the focused test target, fix the
clamping behavior, and then rerun the verifier.

See [expected-output.md](expected-output.md) and [repair-path.md](repair-path.md).
