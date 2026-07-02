# Phase 110: Internal Package Baseline And Ownership

## Status

Completed.

## Goal

Capture pre-refactor behavior and define package ownership before moving any
runtime code into new internal packages.

## Scope

- Run baseline guidance, doctor, fast/precommit verification, pytest, and Tach
  checks from a clean branch.
- Save representative context and guidance artifacts outside the repository for
  comparison during later extraction phases.
- Document package dependency direction in an architecture decision record.
- Align the internal package roadmap with the current DocSync boundary.
- Do not move runtime code.
- Do not add new packages.

## Non-Goals

- No extraction of `agent_repair_facts`, `agent_context`,
  `agent_run_artifacts`, or `agent_client_hooks`.
- No public packaging or distribution change.
- No CLI behavior change.
- No Tach ownership changes for packages that do not exist yet.
- No `docs_evidence` package; DocSync owns docs/evidence traceability.

## Deliverables

- Baseline checks and representative artifacts captured outside the repository.
- [`docs/architecture/decisions/2026-07-02-internal-package-ownership.md`](../../architecture/decisions/2026-07-02-internal-package-ownership.md)
- Updated [`docs/roadmap/internal-package-boundaries.md`](../internal-package-boundaries.md)
- Updated [`docs/roadmap/internal-package-boundaries-implementation-guide.txt`](../internal-package-boundaries-implementation-guide.txt)

## Acceptance Criteria

- Current behavior is captured before any code move.
- Ownership ADR defines each planned internal package and allowed dependency
  direction.
- Roadmap states that DocSync supersedes the earlier `docs_evidence` placeholder.
- No runtime code is moved.
- Checks prove the repository remains green before extraction begins.

## Verification

- `python -m agent_maintainer guidance --check`
- `python -m agent_maintainer doctor`
- `python -m agent_maintainer verify --profile fast`
- `python -m agent_maintainer verify --profile precommit`
- `python -m pytest`
- `tach check --exact`
- Baseline artifacts saved to `/tmp/agent-maintainer-internal-package-baseline-20260702T210136Z`
- Import behavior check for current context, artifact, and hook modules.

## Notes For Future Tasks

Start Phase 111 from a clean branch. Do not move more than one package boundary
per PR. If a proposed extraction makes DocSync duplicate work in another
package, stop and revise the package boundary before editing code.
