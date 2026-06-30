# Phase 58: Quiet Verifier Output Contract

## PR Title

```text
feat: add quiet verifier run details
```

## Scope

Make terminal verifier output explicitly summary-first without moving raw logs
back into agent context. Passing and failing output should expose only compact
run facts: pass/fail, profile, run id, duration, expected profile hint, failed
checks, exact expansion commands, and run-scoped log directory.

## File Targets

```text
src/agent_maintainer/core/reporting.py
src/agent_maintainer/verify/result_summary.py
src/agent_maintainer/verify/timing.py
src/agent_maintainer/verify/artifacts.py
tests/core/test_reporting_artifacts.py
tests/verify/test_artifacts.py
tests/verify/test_verify_quiet.py
docs/agent-maintainer-guidance.md
docs/tool-map.md
```

## Requirements

- Keep raw stdout/stderr in `.verify-logs/runs/<run-id>/`.
- Keep `LAST_FAILURE.md` as latest pointer, not authoritative history.
- Add expected-duration hints per verifier profile.
- Keep output bounded and actionable; do not dump raw command transcripts.
- Preserve existing verifier profiles and exit-code semantics.

## Acceptance Criteria

- Focused tests cover pass/failure output details and manifest hint metadata.
- Style checks pass for touched source files.
- Documentation explains compact terminal summary and run-scoped artifacts.
- Precommit, full, ci, security, manual profiles pass before PR merge.
