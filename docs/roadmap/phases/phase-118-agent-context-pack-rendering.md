# Phase 118: Agent Context Pack Rendering Extraction

Status: complete

## Goal

Move pure context-pack rendering and sanitizing helpers into the reusable
`agent_context` package while preserving the existing `agent-maintainer context`
CLI, hook output, context-pack artifact shape, and compatibility import paths.

## Scope

- Move context-pack Markdown/JSON rendering helpers into `src/agent_context/`.
- Move deterministic text sanitizing helpers into `src/agent_context/`.
- Keep `agent_maintainer.context.pack.rendering` and
  `agent_maintainer.context.pack.sanitize` as compatibility shims.
- Update product modules to import reusable helpers from `agent_context`.
- Update Tach domain contracts so extracted ownership is explicit.
- Add or update direct-package tests for the new `agent_context` modules.
- Keep the phase focused on pure helpers; context-pack building, compression,
  ratchet context, and CLI orchestration remain product-owned.

## Non-goals

- Do not change `context pack` CLI behavior.
- Do not change `PACK.md` or `PACK.json` payload shape.
- Do not change repair capsule wording or hook output budgets.
- Do not move context-pack builder, compression backends, Headroom integration,
  ratchet ranking, or CLI orchestration in this phase.
- Do not remove old import paths.

## Deliverables

- `src/agent_context/pack_rendering.py`
- `src/agent_context/sanitize.py`
- Compatibility shims under `src/agent_maintainer/context/pack/`.
- Focused tests covering rendering/sanitizing through the new package.
- Tach updates for the new modules.
- Architecture decision note for the boundary change.
- Roadmap tracker and index updates.

## Acceptance Criteria

- `agent_context` still does not import `agent_maintainer`.
- Existing context-pack output and hook pointer tests pass.
- Existing imports from `agent_maintainer.context.pack.rendering` and
  `agent_maintainer.context.pack.sanitize` remain valid.
- `tach check --exact` passes.
- `python -m agent_maintainer context pack` remains pointer-first by default.
- All final verifier profiles pass before merge.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/context tests/hooks/test_hook_runtime.py -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer context pack`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile full`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile security`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile manual`

## Notes For Future Agents

This phase intentionally extracts only pure rendering and sanitizing helpers.
If a helper needs `MaintainerConfig`, ratchet modules, compression backend
selection, verifier run state, or CLI arguments, keep it in
`agent_maintainer.context` until a later phase isolates that dependency.
