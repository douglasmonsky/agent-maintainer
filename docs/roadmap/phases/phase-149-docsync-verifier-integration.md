# Phase 149: DocSync Verifier Integration Repair Facts

Status: complete

## Goal

Make DocSync a first-class Agent Maintainer verifier check with structured repair facts and context-pack pointers.

## Primary ROI

Cost medium-high, quality very high, speed high: documentation freshness failures should become exact repair loops.

## Scope

- Create `src/agent_maintainer/runners/docsync.py` using DocSync public API only.
- Add a `docsync` check when `.docsync/trace.yml` exists, at least in precommit, full, and ci.
- Write `.verify-logs/docsync.json`, review packet JSON, review prompt Markdown, and SARIF where feasible.
- Add `agent_repair_facts.parsers.docsync` so DocSync findings become structured repair facts.
- Context packs should prioritize DocSync evidence file/line and include `docsync prompt` expansion guidance.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `tests/docsync/test_agent_maintainer_integration.py`
- `tests/context/test_docsync_repair_facts.py`
- Catalog includes DocSync only when trace exists
- DocSync package still does not import `agent_maintainer`
- `docsync check`
- `python3 -m agent_maintainer verify --profile precommit`
- `tach check --exact`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 149. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
