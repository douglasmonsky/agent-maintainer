+++
id = "context-boundary-and-verifier-artifacts"
kind = "refactor"
status = "active"
base_ref = "origin/main"
expires = 2026-07-13
allowed_paths = ["src/**", "tests/**", "docs/**", "CHANGELOG.md", "AGENTS.agent-maintainer.md", "README.md", "config/pyproject.agent-maintainer.toml", ".agent-maintainer/change-plans/**", "pyproject.toml", "justfile", ".github/workflows/**", "package.json", "package-lock.json", "osv-scanner.toml"]
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
threshold by mixing file/log/diff readers, context pack assembly, compression
adapters, and exact repair fact extraction in one flat folder. The refactor
moves existing modules into explicit `reading`, `pack`, and `compression`
subpackages while preserving CLI behavior.

The same pass also addresses duplicate generated verifier artifacts observed
during overlapping hook/manual runs. Those changes belong with this refactor
because they touch context-pack hook output and verifier artifact ownership.

The branch also enables OSV as a dogfooded manual gate. That requires the CI
installer, npm lock repair, OSV config, and generated active-gate guidance to
move together so the gate is real locally and in CI.

This branch also removes the obsolete documentation graphics render pipeline,
including its `justfile` recipes and Playwright-specific deptry exceptions,
while preserving the committed static PNG assets.

## Why this should not be split smaller

Splitting only the context file moves from import/Tach updates would leave the
branch temporarily broken. Splitting artifact hardening into a later PR would
keep the current duplicate-output failure mode active while the same
context/hook verification paths are already being changed.

The OSV dogfood slice is bounded, but it needs config, CI, npm lock, docs, and
guidance changes together. Without those, the new gate would either not run in
CI or would fail on known dev-tool lockfile state.

## What allowed to change

Allowed changes:

- Context package module boundaries, imports, Tach/domain policy, and tests.
- Verifier artifact locking, run-scoped diagnostics, and duplicate artifact
  prevention.
- Generated agent guidance and human docs for the touched behavior.
- OSV manual-gate activation, CI binary install, OSV config, npm lock repair,
  and focused tests/docs for that activation.

## What must not change

Do not change public CLI command names, verification profile semantics, public
starter scanner defaults, thresholds, package metadata, release publishing
workflow behavior, or unrelated published docs outside the touched checks.

## Verification plan

Run focused tests first:

- `pytest tests/context tests/hooks/test_hook_runtime.py tests/runners/test_secret_scan_runner.py tests/core/test_executor_reporting.py tests/verify/test_locking.py tests/verify/test_verify_quiet.py tests/verify/test_verify_quiet_artifacts.py -q`
- `tach check --exact`
- `osv-scanner scan source -r . --config osv-scanner.toml --format json --output-file .verify-logs/osv-scanner.json`

Then run standard gates:

- `python -m agent_maintainer verify --profile precommit`
- `python -m agent_maintainer verify --profile full`
- `python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main`
- `python -m agent_maintainer verify --profile security`
- `python -m agent_maintainer verify --profile manual`

## Rollback plan

Revert the PR. Old flat context modules and verifier artifact behavior are
contained in the branch and do not require data migration. OSV activation can
also be reverted by removing the repo-local enablement, CI installer, and
`osv-scanner.toml`.

## Follow-up ratchet work

After merge, monitor whether `pack.builder` continues to grow. If it approaches
file/import limits again, split context-pack payload construction and artifact
writing in a dedicated follow-up.
