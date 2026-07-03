+++
id = "agent-run-artifacts-primitives"
kind = "mechanical-migration"
status = "active"
base_ref = "origin/main"
expires = 2026-07-16
allowed_paths = [
  "src/agent_run_artifacts/**",
  "src/{agent_maintainer => agent_run_artifacts}/__init__.py",
  "src/{agent_maintainer/verify => agent_run_artifacts}/artifact_manifest.py",
  "src/{agent_maintainer/verify => agent_run_artifacts}/git_state.py",
  "src/{agent_maintainer/verify => agent_run_artifacts}/history.py",
  "src/{agent_maintainer/verify => agent_run_artifacts}/pr_summary.py",
  "src/{agent_maintainer/verify => agent_run_artifacts}/pr_summary_support.py",
  "src/{agent_maintainer/verify => agent_run_artifacts}/timing.py",
  "src/agent_maintainer/verify/**",
  "src/agent_maintainer/doctor/**",
  "src/agent_maintainer/report/**",
  "tests/verify/**",
  "tests/report/**",
  "docs/**",
  ".agent-maintainer/change-plans/agent-context-primitives.md",
  ".agent-maintainer/change-plans/agent-run-artifacts-primitives.md",
  "AGENTS.agent-maintainer.md",
  "pyproject.toml",
]
forbidden_paths = [
  "config/prod/**",
  ".env",
  ".env.*",
]
max_changed_files = 120
max_changed_lines = 12000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: agent-run-artifacts-primitives

## Why this change intentionally large

This change starts Phase 113 by extracting independent verifier run-artifact
primitives into `agent_run_artifacts`. The touched files are mechanically linked:
run IDs, snapshot paths, safe log copying, atomic writes, timing metadata, and
Git-state helpers are shared by verifier artifact writing, quiet output, report
generation, doctor checks, and tests.

## Why this should not be split smaller

Moving these primitives one file at a time would create temporary mixed import
states and repeated Tach/config/guidance churn. One scoped migration keeps the
boundary reviewable: `agent_run_artifacts` must remain independent from
`agent_maintainer`, while product-coupled manifest and PR-summary rendering can
stay in `agent_maintainer.verify` until their adapters are explicit.

## What allowed to change

- New `src/agent_run_artifacts/**` primitive modules.
- Thin compatibility shims under `src/agent_maintainer/verify/**`.
- Import sites for run IDs, run-scoped snapshot paths, timing, and Git state.
- Tach domain files needed to express the new package boundary.
- Tests that cover new package imports and old-path compatibility.
- Roadmap, ADR, generated guidance, and config path updates for the new source
  root.

## What must not change

- Verifier pass/fail semantics, profile selection, and quiet output wording.
- `.verify-logs` layout, `manifest.json`, `LAST_FAILURE.md`, `pr-summary.md`,
  or run-scoped snapshot shape.
- Manifest payload fields, PR summary sections, context-pack JSON, or hook
  output contract.
- Thresholds, coverage floors, suppression rules, or architecture strictness.
- DocSync, vector, GraphQL, wiki, or retrieval experiment scope.

## Verification plan

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/verify tests/report/test_html_report.py -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer guidance --check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile full`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile security`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile manual`

## Rollback plan

Revert this commit to restore run-artifact primitives under
`agent_maintainer.verify`. Because artifact file names and payload shapes are
unchanged, rollback does not require data or configuration migration.

## Follow-up ratchet work

Finish the rest of Phase 113 in later scoped PRs by extracting product-coupled
manifest and PR-summary renderers behind explicit adapters. Do not move those
renderers into `agent_run_artifacts` until they no longer need
`MaintainerConfig`, `CheckResult`, or product-specific command strings.
