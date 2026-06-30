# Phase 21: CrossHair Candidate Guidance

## PR Title

```text
feat: suggest crosshair contract candidates
```

## Commands

```bash
python -m agent_maintainer test-intel crosshair-candidates
python -m agent_maintainer test-intel crosshair-candidates --changed
python -m agent_maintainer test-intel crosshair-candidates --format json
```

## Candidate Rules

Only include functions that are:

```text
typed
pure
contracted by assert, pre/post docstring, icontract, or deal
free from filesystem/network/subprocess/database access
free from global mutation
bounded enough for analysis
```

## Do Not

Do not run CrossHair automatically in this phase.

## Acceptance Criteria

- Candidate command works.
- Unsafe functions excluded.
- JSON output works.
- Precommit passes.

---
