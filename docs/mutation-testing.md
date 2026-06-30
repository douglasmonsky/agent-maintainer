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

Prefer adding targets after a module has meaningful coverage and stable runtime.
Avoid broad `only_mutate` expansion just to advertise a large mutation surface.

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

Downstream repos keep this off by default. This repo dogfoods it only for
targets that have proven stable enough to block.

## Advisory Sweeps

Use the advisory test-intelligence command to look for future targets:

```bash
python3 -m agent_maintainer test-intel mutation-sweep
```

The sweep ranks candidates by changed files, coverage, complexity, churn, and
existing ratchet hotspots. It should suggest future target promotions, not
silently expand the blocking gate.

See also:

- [Test intelligence](test-intelligence.md)
- [Ratcheting](ratcheting.md)
- [Tool map](tool-map.md)
