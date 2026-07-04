# Phase 155: Claude Async Rewake Hook Option

Status: planned

## Goal

Add an opt-in Claude Code hook install mode that uses async rewake for slow Stop/SubagentStop validation while fast gates stay synchronous.

## Primary ROI

Cost medium-high, quality medium-high, speed medium-high: slow validation should not waste active agent turns.

## Scope

- Add `python3 -m agent_maintainer hooks install claude-code --async-rewake-stop`.
- Default Claude settings remain byte-for-byte unchanged.
- With the option, Stop and SubagentStop entries include `async: true` and `asyncRewake: true`.
- PostToolUse fast hook remains synchronous.
- Dry-run output should show async rewake mode.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `tests/hooks/test_hook_templates.py`
- `tests/hooks/test_agent_client_hooks_package.py`
- Default Claude and Codex template regression tests
- `python3 -m agent_maintainer hooks install claude-code --dry-run --async-rewake-stop`
- `python3 -m agent_maintainer verify --profile fast`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 155. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
