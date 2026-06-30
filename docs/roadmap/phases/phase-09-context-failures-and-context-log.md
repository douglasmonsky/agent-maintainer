# Phase 9: `context failures` and `context log`

## PR Title

```text
feat: add safe context failure and log commands
```

## Files

Create:

```text
src/agent_maintainer/context/cli.py
src/agent_maintainer/context/failures.py
src/agent_maintainer/context/logs.py
```

Update CLI dispatch.

## Commands

```bash
python -m agent_maintainer context failures
python -m agent_maintainer context failures --check pyright
python -m agent_maintainer context failures --limit 20
python -m agent_maintainer context failures --budget 16000
python -m agent_maintainer context failures --format json

python -m agent_maintainer context log pyright --tail 120
python -m agent_maintainer context log pytest-coverage --head 80 --tail 120
python -m agent_maintainer context log ruff --lines 200:260
python -m agent_maintainer context log pyright --budget 20000
python -m agent_maintainer context log pyright --confirm-large
```

## Failure Priority

```text
1. tool/config failures that block meaningful results
2. syntax/import errors
3. type errors in changed files
4. test failures
5. coverage failures
6. architecture violations
7. file-length / structure ratchet violations
8. suppression budget
9. security/tooling findings
10. style/noise
```

## Refusal Message

```text
Requested output is approximately 42,000 characters.
Default budget is 12,000 characters.

Safer options:
  --tail 120              ~9,500 chars
  --lines 300:380        ~7,200 chars
  --budget 50000 --confirm-large
```

## Tests

Create:

```text
tests/context/test_failures.py
tests/context/test_logs.py
```

## Acceptance Criteria

- Help works.
- Missing logs handled gracefully.
- Log slicing works.
- Failure grouping works.
- JSON output works.
- Output bounded.
- Precommit passes.

---
