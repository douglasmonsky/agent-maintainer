# Phase 148: Surgical Context Expansion Ranking

Status: planned

## Goal

Make context-pack hook pointers recommend the narrowest useful next action before broad expansion commands.

## Primary ROI

Cost high, quality medium-high, speed high: agents should inspect the right line or file before loading wider context.

## Scope

- Add or update context next-action selection logic.
- When a repair fact has path and line, first command must be `context file <path> --around <line> --context 30`.
- When a repair fact has path only, first command must be `context file <path> --outline`.
- When only a check is known, prefer `context failures --check <check> --limit 3`, then `context log <check> --tail 80`.
- Keep broad pack/failure commands available, but never first when surgical facts exist.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `tests/context/test_packs.py`
- `tests/context/test_next_actions.py`
- JSON context-pack payload remains backward-compatible
- `python3 -m agent_maintainer context pack`
- `python3 -m agent_maintainer context pack --print-full`
- `python3 -m agent_maintainer verify --profile fast`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 148. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
