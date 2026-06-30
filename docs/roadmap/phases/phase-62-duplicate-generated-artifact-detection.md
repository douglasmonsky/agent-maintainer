# Phase 62: Duplicate Generated Artifact Detection

## PR Title

```text
fix: detect copy-style generated artifacts
```

## Scope

Broaden the existing doctor duplicate-artifact guard so it catches both numeric
Mac-style copies such as `file 2.py` and copy-style generated names such as
`manifest copy 2.json`. This is a cleanup warning, not an automatic deleter.

## File Targets

```text
src/agent_maintainer/doctor/setup.py
tests/doctor/test_doctor_environment.py
docs/ROADMAP.md
```

## Requirements

- Keep scanning constrained to configured generated/source roots already used
  by the duplicate-artifact doctor check.
- Keep status as `WARN`, because users or agents should verify duplicates
  before deleting them.
- Include repair guidance that stale generated duplicates should be inspected
  before removal.

## Acceptance Criteria

- Focused tests cover numeric duplicate names and copy-style names.
- Existing doctor duplicate-artifact tests continue to pass.
- Precommit, full, ci, security, manual profiles pass before PR merge.
