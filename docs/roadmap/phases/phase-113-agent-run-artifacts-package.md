# Phase 113: Agent Run Artifacts Internal Package Extraction

Status: complete

## Goal

Extract verifier run-artifact schemas and rendering helpers into a new internal
sibling package, `agent_run_artifacts`, while preserving current verifier
behavior, `.verify-logs` layout, `manifest.json`, `LAST_FAILURE.md`,
`pr-summary.md`, and old import paths through compatibility shims.

## Why This Phase Follows Agent Context

Run artifacts already depend on bounded context commands, repair facts, timing,
git state, manifest payloads, history retention, and PR summary rendering.
Phase 112 moved the reusable context primitives first. This phase should move
run-artifact ownership next without forcing `agent_run_artifacts` to import
`agent_maintainer` configuration or product orchestration.

## Scope

- Create `src/agent_run_artifacts/`.
- Move run-artifact ownership behind the new package where it can stay
  independent from `agent_maintainer`:
  - `artifact_manifest.py`
  - `history.py`
  - `pr_summary.py`
  - `pr_summary_support.py`
  - `timing.py`
  - `git_state.py`
- Add any required adapter code under `agent_maintainer.verify` when artifact
  rendering needs `MaintainerConfig`, `CheckResult`, or product-specific CLI
  command strings.
- Keep old imports under `agent_maintainer.verify.*` working through thin
  compatibility shims during this extraction pass.
- Update active Agent Maintainer code to import new artifact package modules
  where safe.
- Update Tach domain files, `[tool.agent_maintainer]` package/source paths,
  Semgrep paths, deptry first-party packages, generated guidance, and the
  internal package ownership ADR.
- Add direct tests for `agent_run_artifacts` plus compatibility tests for old
  `agent_maintainer.verify.*` import paths.
- Compare representative run artifacts before and after the move using
  semantic checks that ignore run IDs, timestamps, and absolute temp paths.

## Non-Goals

- Do not change verifier pass/fail semantics.
- Do not change profile selection, check execution, or quiet output wording.
- Do not change `manifest.json`, `LAST_FAILURE.md`, `pr-summary.md`, or
  run-scoped snapshot layout except through explicit compatibility-preserving
  adapter changes.
- Do not extract hook packages in this phase.
- Do not move context-pack builder/rendering, compression, ratchet context, or
  context CLI ownership into `agent_context`.
- Do not add vector, GraphQL, wiki, retrieval, or DocSync knowledge-graph code.
- Do not publish a separate `agent-run-artifacts` distribution.

## Acceptance Criteria

- `src/agent_run_artifacts/` exists and does not import `agent_maintainer`.
- Existing imports from `agent_maintainer.verify.artifact_manifest`,
  `agent_maintainer.verify.history`, `agent_maintainer.verify.pr_summary`,
  `agent_maintainer.verify.pr_summary_support`,
  `agent_maintainer.verify.timing`, and `agent_maintainer.verify.git_state`
  continue working through compatibility shims.
- Active verifier code uses new package imports where the dependency direction
  is clean.
- Artifact rendering still writes stable:
  - `.verify-logs/manifest.json`
  - `.verify-logs/LAST_FAILURE.md`
  - `.verify-logs/pr-summary.md`
  - `.verify-logs/runs/<run-id>/manifest.json`
  - `.verify-logs/runs/<run-id>/LAST_FAILURE.md`
  - copied safe check logs inside run-scoped snapshots.
- PR summary sections remain stable: result, failed checks, warnings, skipped
  checks, test intelligence, ratchet targets, technical debt, change budget,
  change plan status, context pack path, and expansion commands.
- Tach exact mode accounts `agent_run_artifacts` without broad root buckets.
- `[tool.agent_maintainer]` paths include `src/agent_run_artifacts` where
  source/package/coverage/file-length/structure/vulture/Semgrep checks need it.
- Direct new-package tests and old-path compatibility tests pass.
- Normal verification profiles pass with only existing expected warnings.

## Characterization Before Moving Code

- Capture representative artifact output from current `main` before moving
  files:
  - a passing `precommit` run manifest.
  - a controlled failed run manifest or artifact fixture.
  - `LAST_FAILURE.md`.
  - `pr-summary.md`.
  - run-scoped snapshot manifest/log paths.
- Add or reuse semantic artifact assertions that compare structure and
  user-visible fields while ignoring run IDs, timestamps, elapsed durations,
  and temp-directory-specific paths.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/verify -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer guidance --check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile full`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile security`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile manual`

## Focused Evidence

- `agent_run_artifacts` owns artifact manifest payloads, run history helpers,
  Git-state helpers, PR summary helpers, and timing helpers without importing
  `agent_maintainer`.
- Compatibility shims remain under `agent_maintainer.verify.*`.
- Focused artifact/report tests pass, including old-path compatibility tests.
- Ruff, focused source Pyright, Tach exact, generated guidance, and change-plan
  checks pass locally before final verifier profiles.

## Notes For Future Codex Tasks

- Move one artifact module cluster at a time if dependencies show
  `agent_maintainer` back-pressure.
- Keep adapters in `agent_maintainer.verify` instead of letting
  `agent_run_artifacts` import product config or CLI orchestration.
- If artifact JSON or markdown shape changes, stop and make that an explicit
  behavior-change phase rather than hiding it inside this package extraction.
- Keep the graph/vector/GraphQL/wiki prototype on the experimental branch until
  DocSync core workflows prove the need for retrieval.
