# Mutation Testing

Agent Maintainer supports mutation testing through Mutmut, but the default
product stance is targeted and ratcheted rather than broad mutation everywhere.

## Normal Gate

Mutation testing belongs in the `manual` profile:

```bash
python3 -m agent_maintainer verify --profile manual
```

This keeps pre-commit and normal CI responsive while still allowing mature repos
to block on stable mutation targets.

## Targeted Configuration

Use Mutmut's project config to keep the blocking surface intentional:

```toml
[tool.mutmut]
mutate_only_covered_lines = true
only_mutate = ["src/my_package/core.py"]
max_stack_depth = 8
```

Prefer targets after module behavior, coverage, and runtime are stable. Avoid
broad `only_mutate` expansion just to advertise a large mutation surface.

## Result Ratchets

Agent Maintainer can ratchet mutation results when enabled:

```toml
[tool.agent_maintainer]
enable_mutmut = true
mutmut_result_ratchet_enabled = true
mutmut_max_survivors = 0
mutmut_max_suspicious = 0
mutmut_max_timeouts = 0
mutmut_min_score = 90
```

Downstream repos keep this off by default. This repo dogfoods only targets that
have proven stable enough to block.

## Advisory Sweeps

Use the advisory test-intelligence command to look for future targets:

```bash
python3 -m agent_maintainer test-intel mutation-sweep
```

The sweep ranks candidates by changed files, coverage, complexity, churn, and
existing ratchet hotspots. Planner mode does not run Mutmut. It suggests future
target promotions, not silent blocking-gate expansion.

Use non-default execution mode when you want measured Mutmut data for the ranked
candidates without editing `pyproject.toml` by hand:

```bash
python3 -m agent_maintainer test-intel mutation-sweep \
  --execute --candidate-limit 2 --target-limit 10 --time-budget-minutes 60
```

Execution copies the repository to temporary worktrees, patches
`[tool.mutmut].only_mutate` and likely focused tests only in those copies, runs
Mutmut there, and writes raw logs plus stats snapshots under
`.verify-logs/mutation-sweeps/<run-id>/`. Terminal output stays summary-first:
candidate, score, killed/total, survivors, suspicious/timeouts, promotion
readiness, and artifact path.

Promotion readiness is advisory. A candidate is ready to consider for the
blocking manual gate only when survivor count is at or below the configured
threshold, suspicious and timeout counts are zero, and the runner completed
successfully.

Current dogfood findings:

- `src/agent_maintainer/core/reporting.py`: reduced from 124 to 39 survivors,
  still not promotion-ready.
- `src/agent_maintainer/doctor/cli.py`: reduced from 270 to 11 survivors after
  splitting environment, integration, and output helpers out of the CLI module;
  still not promotion-ready.

See also:

- [Test intelligence](test-intelligence.md)
- [Ratcheting](ratcheting.md)
- [Tool map](tool-map.md)
