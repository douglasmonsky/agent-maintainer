# Mutation Sweep Executor Boundary

## Status

Accepted.

## Context

The advisory mutation sweep planner ranked useful Mutmut candidates but still
required manual `pyproject.toml` edits to test them. Dogfooding showed this was
too easy to run noisily and too easy to leave config or generated artifacts in
the source checkout.

## Decision

Add dedicated test-intelligence modules for mutation sweep execution:

- `mutation_sweep_execution` owns execution request/result data.
- `mutation_sweep_config` patches Mutmut config only inside copied worktrees.
- `mutation_sweep_runner` owns temp worktree setup, Mutmut process execution,
  stats collection, and promotion readiness checks.
- `mutation_sweep_executor` orchestrates ranked candidate execution and
  run-scoped artifacts.

The Tach contract explicitly assigns each module instead of broadening the
`test_intel` root. Execution remains advisory and manual; blocking Mutmut
promotion still belongs to the existing `[tool.mutmut]` target list and manual
profile.

## Alternatives Considered

Inlining the executor into `mutation_sweep.py` or `mutation_sweep_cli.py` was
rejected because it mixed planning, CLI parsing, process execution, config
patching, and artifact rendering in one boundary. Adding a verifier profile was
also rejected because deep mutation sweeps are still research/advisory work.

## Still Forbidden

Do not mutate the source checkout's `pyproject.toml` during advisory sweeps. Do
not expand blocking Mutmut targets just because a candidate appears in sweep
output. Do not make broad mutation sweeps part of precommit, full, or CI
verification.
