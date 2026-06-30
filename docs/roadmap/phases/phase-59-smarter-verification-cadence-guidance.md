# Phase 59: Smarter Verification Cadence Guidance

## PR Title

```text
feat: recommend focused verifier reruns
```

## Scope

Keep the final verification bar strict while improving inner-loop guidance.
Failure summaries should recommend the smallest useful rerun command. If one
check fails and the check command is available, print that command. If several
checks fail or command metadata is unavailable, fall back to the current
verifier profile.

## File Targets

```text
src/agent_maintainer/core/reporting.py
src/agent_maintainer/verify/result_summary.py
tests/verify/test_result_summary.py
docs/agent-maintainer-guidance.md
docs/roadmap/full-roadmap-blueprint.md
docs/ROADMAP.md
```

## Requirements

- Do not weaken profile gates.
- Do not add raw command output to terminal summaries.
- Preserve existing profile fallback for multi-check failures.
- Keep docs aligned with the cadence: focused tests during edit loops,
  precommit before commit, full/ci/security/manual before PR or merge.

## Acceptance Criteria

- Unit tests cover single failure command selection and fallback cases.
- Focused style/tests pass.
- Precommit, full, ci, security, manual profiles pass before PR merge.
