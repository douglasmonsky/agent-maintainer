# Phase 119: Agent Context Compression Extraction

Status: complete

## Goal

Move reusable context compression request/result contracts, deterministic
compression backends, and the optional Headroom adapter into `agent_context`
while preserving current context-pack CLI behavior, fallback semantics, and
compatibility import paths.

## Scope

- Add `src/agent_context/compression/` modules for models, backends, and
  Headroom integration.
- Keep `agent_maintainer.context.compression.*` as compatibility shims.
- Update product-owned context-pack compression orchestration to import reusable
  compression primitives from `agent_context`.
- Update Tach domain contracts to make ownership explicit.
- Add or update direct-package and compatibility tests.
- Add an architecture decision note for the boundary change.

## Non-goals

- Do not change compression backend names.
- Do not change `context pack` CLI flags or config behavior.
- Do not change `PACK.md` or `PACK.json` payload shape.
- Do not move context-pack compression orchestration, builder, ratchet context,
  or CLI handling out of `agent_maintainer`.
- Do not remove old import paths.
- Do not add Headroom back as an active default integration.

## Deliverables

- `src/agent_context/compression/models.py`
- `src/agent_context/compression/headroom.py`
- `src/agent_context/compression/backends.py`
- Compatibility shims under `src/agent_maintainer/context/compression/`.
- Product imports updated to use `agent_context.compression`.
- Tach updates for the new compression modules.
- Focused tests for new package imports and old-path compatibility.
- Architecture decision note.
- Roadmap tracker and index updates.

## Acceptance Criteria

- `agent_context` still does not import `agent_maintainer`.
- Existing compression and context-pack compression tests pass.
- Existing imports from `agent_maintainer.context.compression.*` remain valid.
- `python -m agent_maintainer context pack` remains pointer-first by default.
- `tach check --exact` passes.
- All final verifier profiles pass before merge.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/context tests/hooks/test_hook_runtime.py tests/architecture/test_internal_package_boundaries.py -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer context pack`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile full`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile security`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile manual`

## Notes For Future Agents

This phase intentionally extracts the lower-level compression primitives only.
If a helper needs `MaintainerConfig`, context-pack request wiring, CLI flags, or
ratchet context, keep it under `agent_maintainer.context` until a later phase.
