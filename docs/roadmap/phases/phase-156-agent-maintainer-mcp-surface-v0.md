# Phase 156: Agent Maintainer MCP Surface v0

Status: planned

## Goal

Expose highest-return Agent Maintainer commands through a typed tool surface while keeping CLI primary.

## Primary ROI

Cost medium-high, quality medium-high, speed high: schema-backed tools reduce shell guessing.

## Scope

- Create `src/agent_maintainer/mcp/` with models, tools, and server.
- Add optional `mcp` dependency extra; core install must not require MCP dependencies.
- Expose verify, context failures, context pack pointer, context file, events summary, attention, and DocSync tools.
- Add `python3 -m agent_maintainer mcp serve`.
- If MCP dependencies are missing, exit 2 with installation guidance.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `tests/mcp/test_mcp_tools.py`
- `python3 -m agent_maintainer mcp serve --help`
- Missing-dependency behavior test
- `python3 -m agent_maintainer verify --profile fast`
- `tach check --exact`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 156. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
