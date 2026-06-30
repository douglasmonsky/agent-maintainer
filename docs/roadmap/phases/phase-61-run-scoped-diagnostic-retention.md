# Phase 61: Run-Scoped Diagnostic Retention

## PR Title

```text
feat: harden diagnostic artifact retention
```

## Scope

Finish the run-scoped artifact safety pass. The config field
`diagnostic_run_history_limit` already defaults to `10` and pruning already
keeps recent run directories. Harden the remaining operational details: unique
run IDs for same-second verifier starts, deterministic retention ordering, and
atomic replacement of latest diagnostic pointers.

## File Targets

```text
src/agent_maintainer/verify/artifacts.py
src/agent_maintainer/verify/history.py
tests/verify/test_artifacts.py
docs/ROADMAP.md
```

## Requirements

- Keep `.verify-logs/runs/<run-id>/` authoritative for retained snapshots.
- Keep `LAST_FAILURE.md` a convenience pointer.
- Replace latest manifest, failure pointer, and PR summary atomically.
- Retain newest run directories deterministically.
- Keep `diagnostic_run_history_limit = 10` as the default.

## Acceptance Criteria

- Focused tests cover atomic writes, run-id timestamp precision, and retention
  tie-breaking.
- Existing run snapshot tests continue to pass.
- Precommit, full, ci, security, manual profiles pass before PR merge.
