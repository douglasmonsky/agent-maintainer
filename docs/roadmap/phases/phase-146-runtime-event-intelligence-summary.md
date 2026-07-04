# Phase 146: Runtime Event Intelligence Summary CLI

Status: completed

## Goal

Turn local runtime event JSONL files into compact, agent-usable summaries.

## Primary ROI

Cost high, quality medium-high, speed high: runtime events already exist; this phase makes them queryable.

## Scope

- Create `src/agent_maintainer/runtime_events/read.py`, `summary.py`, and `cli.py`.
- Add `agent-maintainer events summary`, `events failures`, `events slow-checks`, and `events recent` with text and JSON output.
- Ignore missing event dirs and malformed lines safely while counting malformed lines.
- Summarize profile runs, check finish status, failed checks, latest failures, skips, and slow checks when duration exists.
- Keep output deterministic and do not fake missing duration data.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `tests/runtime_events/test_runtime_event_reading.py`
- `tests/runtime_events/test_runtime_event_summary.py`
- `tests/runtime_events/test_runtime_event_cli.py`
- `python3 -m agent_maintainer events summary --format json`
- `python3 -m agent_maintainer verify --profile fast`
- `tach check --exact`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 146. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
