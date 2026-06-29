+++
id = "context-boundary-and-verifier-artifacts"
kind = "refactor"
status = "active"
base_ref = "origin/main"
expires = 2026-07-13
allowed_paths = ["src/**", "tests/**", "docs/**", "AGENTS.agent-maintainer.md", "README.md", "config/pyproject.agent-maintainer.toml", ".agent-maintainer/change-plans/**", "pyproject.toml"]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 120
max_changed_lines = 12000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: context-boundary-and-verifier-artifacts

## Why this change intentionally large

The `agent_maintainer.context` package crossed the structure-cohesion warning
threshold and mixed file/log/diff readers, context pack assembly, compression
adapters, and exact repair fact extraction in one flat folder. The refactor
moves those existing modules into explicit `reading`, `pack`, and `compression`
subpackages while preserving CLI behavior.

The same pass also addresses duplicate generated verifier artifacts observed
during overlapping hook/manual runs. Those changes belong with this refactor
because they touch context-pack hook output and verifier artifact ownership.

## Why this should not be split smaller

Splitting only the file moves from the import/Tach updates would leave the
branch temporarily broken. Splitting the artifact hardening into a later PR
would keep the current duplicate-output failure mode active while the same
context/hook verification paths are being changed.

The change remains bounded: no new scanners, no threshold changes, no policy
relaxation, and no behavior change outside context packaging plus canonical
verifier artifacts.

## What allowed to change

Allowed changes:

- `src/agent_maintainer/context/**` package layout, imports, and Tach domain
  contract.
- Hook context imports that point at moved context-pack modules.
- `src/agent_maintainer/verify/**`, `src/agent_maintainer/core/executor.py`,
  and `src/agent_maintainer/runners/secret_scan.py` for state-aware verifier
  locking and canonical artifact handling.
- Generated guidance, README, and starter config updates documenting
  diagnostics history and compact agent context.
- Focused tests under `tests/context`, `tests/hooks`, `tests/verify`,
  `tests/core`, and `tests/runners`.
- Architecture decision notes documenting the boundary and lock changes.

## What must not change

Do not change public CLI command names, verification profile semantics, scanner
enablement defaults, thresholds, package metadata, release workflow behavior, or
published docs outside the architecture notes required for Tach changes.

## Verification plan

Run focused tests first:

- `pytest tests/context tests/hooks/test_hook_runtime.py tests/runners/test_secret_scan_runner.py tests/core/test_executor_reporting.py tests/verify/test_locking.py tests/verify/test_verify_quiet.py tests/verify/test_verify_quiet_artifacts.py -q`
- `tach check --exact`

Then run standard gates:

- `python -m agent_maintainer verify --profile precommit`
- `python -m agent_maintainer verify --profile full`
- `python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main`
- `python -m agent_maintainer verify --profile security`
- `python -m agent_maintainer verify --profile manual`

## Rollback plan

Revert the PR. The old flat context modules and verifier artifact behavior are
contained in this branch and do not require data migration.

## Follow-up ratchet work

After merge, monitor whether `pack.builder` continues to grow. If it approaches
file/import limits again, split context-pack payload construction from artifact
writing in a dedicated follow-up.
