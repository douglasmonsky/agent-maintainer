# Phase 57: Advisory Deep Mutation Sweep

## PR Title

```text
feat: add advisory mutation sweep planner
```

## Scope

Add `python -m agent_maintainer test-intel mutation-sweep` as an advisory,
non-default planning command. It must not run Mutmut by default. It should rank
candidate modules using changed-file signal, likely focused tests, coverage
artifacts, complexity, recent Git churn, and ratchet hotspots.

## File Targets

```text
src/agent_maintainer/test_intel/mutation/sweep.py
src/agent_maintainer/test_intel/mutation/sweep_reporting.py
src/agent_maintainer/test_intel/mutation/sweep_cli.py
src/agent_maintainer/test_intel/cli.py
tests/test_intel/test_mutation_sweep.py
docs/test-intelligence.md
docs/tool-map.md
```

## Requirements

- Output text and JSON reports.
- Include stop conditions: time budget, target limit, survivor threshold, and
  no-new-findings behavior.
- Recommend `[tool.mutmut].only_mutate` promotions and the manual verification
  command instead of pretending Mutmut has a path-targeting CLI flag.
- Keep broad sweeps advisory. Do not add the command to normal verification
  profiles.
- Keep the main `test_intel.cli` module below current style/import thresholds.

## Acceptance Criteria

- Focused sweep tests cover ranking, rendering, and changed-source error
  handling.
- `python -m agent_maintainer test-intel mutation-sweep --format json` works.
- Tach explicitly assigns new modules.
- Documentation explains advisory status and targeted blocking workflow.
- Precommit, full, ci, security, manual profiles pass before PR merge.
