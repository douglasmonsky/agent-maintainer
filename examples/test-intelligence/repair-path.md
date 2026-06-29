# Repair Path

1. Run `pytest tests/test_rubric.py -q`.
2. Run `agent-maintainer test-intel changed --base-ref HEAD`.
3. Fix `clamp_score` so scores above `maximum` return `maximum`.
4. Keep the focused regression test.
5. Run `pytest tests/test_rubric.py -q`.
6. Run `agent-maintainer verify --profile precommit --base-ref HEAD`.
