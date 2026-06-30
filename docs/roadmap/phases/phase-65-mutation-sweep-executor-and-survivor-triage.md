# Phase 65: Mutation Sweep Executor and Survivor Triage

## PR Title

```text
feat: execute advisory mutation sweeps safely
```

## Scope

Extend `python -m agent_maintainer test-intel mutation-sweep` with a
non-default execution mode. The existing planner remains unchanged unless
`--execute` is provided. Execution must run Mutmut in an isolated temporary
worktree, patch Mutmut targets only in that copy, and collect compact
artifact-backed results under `.verify-logs/mutation-sweeps/<run-id>/`.

## File Targets

```text
src/agent_maintainer/test_intel/mutation_sweep.py
src/agent_maintainer/test_intel/mutation_sweep_cli.py
src/agent_maintainer/test_intel/mutation_sweep_reporting.py
src/agent_maintainer/test_intel/mutation_sweep_executor.py
tests/test_intel/test_mutation_sweep.py
tests/test_intel/test_mutation_sweep_executor.py
docs/mutation-testing.md
docs/test-intelligence.md
docs/tool-map.md
tach.toml
```

## Requirements

- Add `mutation-sweep --execute` as an advisory manual command.
- Add execution options:
  - `--candidate-limit N`, default `1` with `--execute`;
  - `--output-dir PATH`, default `.verify-logs/mutation-sweeps`;
  - `--keep-worktree`;
  - `--fail-fast`.
- Keep planner behavior and JSON/text output unchanged when `--execute` is
  absent.
- Copy the repository to a temporary worktree for each executed candidate.
- Patch `[tool.mutmut].only_mutate` and focused test selection only in the
  temporary worktree.
- Capture raw Mutmut progress and logs into artifacts, not agent-facing
  output.
- Emit a quiet summary with candidate path, score, killed/total, survivor
  count, suspicious/timeouts, promotion readiness, and artifact path.
- Mark candidates promotion-ready only when survivor count is at or below the
  configured threshold, suspicious and timeout counts are zero, and the runner
  completed successfully.
- Default execution exits nonzero only for executor/config/runner failures, not
  for ordinary survivor counts.
- Preserve the current blocking `[tool.mutmut]` target list until deep-sweep
  results prove a candidate is stable enough to promote.
- Dogfood execution on:
  - `src/agent_maintainer/core/reporting.py`;
  - `src/agent_maintainer/doctor/cli.py`.

## Acceptance Criteria

- Focused tests cover planner behavior without `--execute`.
- Focused tests cover temp config patching without modifying repo
  `pyproject.toml`.
- Focused tests cover candidate limit, time budget, raw-output capture,
  promotion readiness, runner failure, and `--fail-fast`.
- Fake-Mutmut integration test proves temp worktree creation, stats collection,
  cleanup, and manifest writing.
- Documentation records current dogfood findings:
  - `src/agent_maintainer/core/reporting.py`: 124 survivors, not
    promotion-ready.
  - `src/agent_maintainer/doctor/cli.py`: 270 survivors, not
    promotion-ready.
- Normal manual Mutmut gate still passes after executor runs.
- No `mutants/`, `__pycache__`, `*.pyc`, or duplicate generated files remain.
- `python -m agent_maintainer guidance --check` passes.
- `python -m agent_maintainer change-plan check` passes.
- `tach check --exact` passes.
- Precommit, full, ci, security, and manual profiles pass before PR merge.
