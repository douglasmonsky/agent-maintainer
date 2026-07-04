# Phase 147: Repair-Fact Coverage Score

Status: completed

## Goal

Measure which failing checks produce structured repair facts and which still force raw-log expansion.

## Primary ROI

Cost high, quality high, speed high: parser gaps directly drive token-heavy repair loops.

## Scope

- Create `src/agent_maintainer/assess/repair_fact_coverage.py`.
- Add `agent-maintainer assess repair-fact-coverage` and `--json`.
- Analyze latest run-scoped manifest data under `.verify-logs`.
- Treat facts as structured when they include a check, message, and at least one of path, line, rule, or symbol.
- Rank next parser targets by recent failure frequency, fallback count, raw log size, and check priority.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `tests/assess/test_repair_fact_coverage.py`
- No-manifest, no-failure, structured, fallback, mixed, deterministic ranking, and JSON round-trip cases
- `python3 -m agent_maintainer assess repair-fact-coverage --json`
- `python3 -m agent_maintainer verify --profile fast`
- `tach check --exact`

## Notes For Future Tasks

Implemented as `python -m agent_maintainer assess repair-fact-coverage`.
The command reports latest-run structured repair-fact coverage, keeps output
summary-first, and ranks recent fallback parser targets from run-scoped
manifests. Current dogfood output shows the latest run has no failures while
recent history still ranks `architecture-decision` as a parser gap.

Treat this file as the implementation authority for Phase 147. Keep follow-up
work scoped to Phase 148 unless the user explicitly asks to bundle phases.
