# Expected Output

```text
change-plan check: reports one active valid plan
verify --profile precommit: enforces source/test coverage and change scope
```

If a change touches paths outside `src/catalog/**` or `tests/**`, the plan
should fail scope validation.
