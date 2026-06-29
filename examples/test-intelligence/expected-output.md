# Expected Output

```text
test-intel changed: lists changed source files and likely focused tests
hypothesis-candidates: suggests pure branchy functions worth property tests
crosshair-candidates: suggests typed functions that may accept contracts
verify --profile precommit: fails until score clamping is fixed
```

The exact candidate order can change as the fixture evolves, but the output
should point the agent toward `src/scoring/rubric.py` and `tests/test_rubric.py`.
