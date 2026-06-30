# Phase 6: Bounded Verifier, Hook, and LAST_FAILURE Output

## PR Title

```text
feat: bound verifier failure context
```

## Goal

Use the context contract to cap all failure-oriented outputs.

## Files

Update:

```text
src/agent_maintainer/verify/artifacts.py
src/agent_maintainer/verify/reporting.py
src/agent_maintainer/verify/executor.py
src/agent_maintainer/hooks/runtime.py
```

## Behavior

All failure summaries must:

```text
cap output
state omitted chars/lines/items
include expansion commands
preserve exact facts
write full output to logs/artifacts
```

Manifest entries must include:

```json
{
  "log_bytes": 12345,
  "summary_chars": 8000,
  "summary_truncated": true,
  "omitted_chars": 123456,
  "omitted_lines": 2222,
  "expansion_commands": []
}
```

`LAST_FAILURE.md` must use `context_last_failure_budget_chars`.

Hook output must use `context_hook_budget_chars`.

## Placeholder Expansion Commands

Even before the commands work, include stable commands:

```text
python -m agent_maintainer context failures --check <check> --limit 20
python -m agent_maintainer context log <check> --tail 120
```

## Tests

Create/update:

```text
tests/context/test_bounded_failure_output.py
tests/verify/test_bounded_failure_output.py
tests/hooks/test_context_budget.py
```

Use artificial large output.

## Acceptance Criteria

- Huge failure output is capped.
- Hook output is capped.
- LAST_FAILURE.md is capped.
- Manifest includes size metadata.
- Precommit passes.

---
