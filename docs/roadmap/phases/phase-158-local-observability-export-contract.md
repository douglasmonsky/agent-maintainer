# Phase 158: Local Observability Export Contract

Status: planned

## Goal

Define a local export seam for runtime events and task-broker outcomes without selecting a hosted backend.

## Primary ROI

Cost medium, quality medium-high, speed medium: local event contracts should be exportable later.

## Scope

- Create `src/agent_maintainer/runtime_events/export.py`.
- Add `agent-maintainer events export --format jsonl` and `--format otel-json`.
- `otel-json` is a local OpenTelemetry-shaped JSON representation, not a network exporter.
- No external service dependency, no network calls, no secrets.
- Preserve event source file and line number where available.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `tests/runtime_events/test_runtime_event_export.py`
- `python3 -m agent_maintainer events export --format jsonl`
- `python3 -m agent_maintainer events export --format otel-json`
- `python3 -m agent_maintainer verify --profile fast`
- `tach check --exact`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 158. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
