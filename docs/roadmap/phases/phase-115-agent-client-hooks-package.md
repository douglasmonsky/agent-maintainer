# Phase 115: Agent Client Hooks Internal Package Extraction

Status: complete

## Goal

Extract agent-client hook templates, config merge helpers, and installation
planning into the internal `agent_client_hooks` package while preserving
existing `agent-maintainer hooks ...` behavior.

Runtime verification remains product-owned under `agent_maintainer.hooks`.
The new package should own only client-facing configuration and generated
wrapper templates.

## Scope

- Create `src/agent_client_hooks/`.
- Move hook client constants, templates, merge helpers, adapter models, adapter
  selection, and path planning into `agent_client_hooks`.
- Keep `agent_maintainer.hooks.templates`, `agent_maintainer.hooks.adapters`,
  and `agent_maintainer.hooks.merge` as compatibility shims.
- Update `agent_maintainer.hooks.manager` and runtime imports to consume the
  new package where appropriate.
- Add direct tests for `agent_client_hooks` and preserve old import-path tests.
- Update Tach contracts, Agent Maintainer source/package paths, static-analysis
  paths, and generated guidance for the new package.
- Add an architecture decision note for the package boundary change.

## Non-Goals

- Do not change hook install CLI behavior.
- Do not change Codex or Claude generated config semantics.
- Do not move hook runtime verification, audit logging, context assembly, or
  subprocess execution out of `agent_maintainer`.
- Do not remove old `agent_maintainer.hooks.*` import paths in this pass.
- Do not add support for new agent clients.

## Acceptance Criteria

- `agent_client_hooks` exists and does not import `agent_maintainer`.
- Product-owned runtime modules stay under `agent_maintainer.hooks`.
- Existing hook installation, merge, template, and runtime tests pass.
- New direct-package tests prove the extracted package owns templates/adapters.
- Tach exact mode accounts for the new package without a permissive root bucket.
- Generated guidance includes `src/agent_client_hooks` in source roots.
- All verifier profiles pass with only expected warnings.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/hooks -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m ruff check src/agent_client_hooks src/agent_maintainer/hooks tests/hooks`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer guidance --check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile full`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile security`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile manual`

## Notes For Future Agents

Treat `agent_client_hooks` as template/config-planning infrastructure, not as
the verifier runtime. If a helper needs `MaintainerConfig`, verifier result
objects, audit logging, context packs, or subprocess execution, keep that code
in `agent_maintainer.hooks` behind an adapter.
