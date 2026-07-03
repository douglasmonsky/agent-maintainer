<!-- docsync:object docs.mutation_testing.overview -->
# Mutation Testing

Agent Maintainer supports mutation testing through Mutmut, but its default
product stance is targeted and ratcheted, not broad mutation everywhere.

## Normal Gate

Mutation testing belongs in the `manual` profile:

```bash
python3 -m agent_maintainer verify --profile manual
```

This keeps pre-commit and normal CI responsive while still allowing mature
repositories to block on stable mutation targets.

## Targeted Configuration

Use Mutmut's project config to keep the blocking surface intentional:

```toml
[tool.mutmut]
mutate_only_covered_lines = true
only_mutate = ["src/my_package/core.py"]
max_stack_depth = 8
```

Prefer targets with stable behavior, coverage, and runtime. Avoid broad
`only_mutate` expansion just to advertise a larger mutation surface.

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

Downstream repositories keep this off by default. This repository dogfoods it
only for targets that have proven stable enough to block.

## Advisory Sweeps

Use the advisory test-intelligence command to find future targets:

```bash
python3 -m agent_maintainer test-intel mutation-sweep
```

Planner mode does not run Mutmut. It ranks candidates by changed files,
coverage, complexity, churn, and existing ratchet hotspots, then suggests
future target promotions instead of silently expanding the blocking gate.

Use non-default execution mode when you want measured Mutmut data for ranked
candidates without editing `pyproject.toml` by hand:

```bash
python3 -m agent_maintainer test-intel mutation-sweep \
  --execute --candidate-limit 2 --target-limit 10 --time-budget-minutes 60
```

Execution copies the repository to temporary worktrees, patches
`[tool.mutmut].only_mutate` and likely focused tests only inside those copies,
runs Mutmut there, and writes raw logs plus stats snapshots under
`.verify-logs/mutation-sweeps/<run-id>/`. Terminal output stays summary-first:
candidate, score, killed/total, survivors, suspicious/timeouts, promotion
readiness, and artifact path.

Promotion readiness is advisory. Consider a candidate for the blocking manual
gate only when survivor count is below the configured threshold,
suspicious/timeout counts are zero, and the runner completes successfully.

## Current Dogfood Findings

- Blocking manual target set: `343/345` killed, `2` survivors, `99.42%`
  mutation score, `0` suspicious, and `0` timeout outcomes from run
  `20260703T093525586771Z-manual-e0f7c77bcdc3`.
- Remaining blocking-target survivors are encoding-equivalent mutations in
  `targets_for_source`.
- `src/agent_maintainer/core/reporting.py`: reduced from 124 to 39 survivors,
  still not promotion-ready.
- `src/agent_maintainer/doctor/cli.py`: reduced from 270 to 11 survivors after
  splitting environment, integration, and output helpers out of the CLI module;
  still not promotion-ready.

See also:

- [Test intelligence](test-intelligence.md)
- [Ratcheting](ratcheting.md)
- [Tool map](tool-map.md)
<!-- docsync:object.end docs.mutation_testing.overview -->
