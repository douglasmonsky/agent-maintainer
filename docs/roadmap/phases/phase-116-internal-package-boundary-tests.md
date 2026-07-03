# Phase 116: Internal Package Boundary Regression Tests

Status: complete

## Goal

Make the extracted internal-package dependency direction executable with focused
tests before continuing package extraction or deeper DocSync dogfooding.

## Scope

- Remove the completed Phase 115 active change plan.
- Add architecture tests that scan extracted package imports.
- Enforce that reusable packages do not import `agent_maintainer`.
- Enforce DocSync's existing boundary against `agent_maintainer` and
  `archguard`.
- Keep package-specific compatibility tests intact.

## Non-goals

- No runtime behavior changes.
- No new packages.
- No Tach relaxation.
- No DocSync trace expansion.
- No shim cleanup decision.

## Deliverables

- `tests/architecture/test_internal_package_boundaries.py`
- This phase entry.
- Roadmap index updates.
- Completed-work note in `docs/ROADMAP.md`.
- Removal of stale completed change-plan override state.

## Acceptance Criteria

- Tests fail if `agent_context`, `agent_repair_facts`, `agent_run_artifacts`,
  `agent_client_hooks`, or `docsync` import forbidden product packages.
- Tests allow each package's intended internal dependencies.
- `tach check --exact` remains green.
- Existing hook package tests remain green.
- No user-facing behavior changes.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/architecture/test_internal_package_boundaries.py tests/hooks/test_agent_client_hooks_package.py -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer guidance --check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile full`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile security`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile manual`

## Notes For Future Tasks

Use this regression test when extracting remaining product-owned primitives.
If a package genuinely needs a new dependency, update the test and the relevant
architecture decision in the same PR.
