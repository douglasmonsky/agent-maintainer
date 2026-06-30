# Phase 66: Advisory Sweep Survivor Triage

## PR Title

```text
test: reduce advisory mutation survivors
```

## Scope

Use advisory mutation sweep results to improve test coverage without promoting
unstable targets into the blocking Mutmut gate. Start with
`src/agent_maintainer/core/reporting.py`, then handle
`src/agent_maintainer/doctor/cli.py` separately.

## Requirements

- Keep current blocking Mutmut targets unchanged unless a candidate becomes
  promotion-ready.
- Run the advisory sweep executor for `core/reporting.py` first.
- Inspect survivor clusters from generated artifacts, not terminal transcripts.
- Add focused tests for reporting output summary, failed-check rendering,
  artifact links, and next-command selection.
- Rerun advisory sweep and record before/after survivor counts in
  `docs/mutation-testing.md`.
- Treat `doctor/cli.py` as refactor-first if survivors cluster around command
  plumbing.
- Add pure-helper tests for doctor formatting and exit-code decisions before
  mutation assertions.

## Acceptance Criteria

- `core/reporting.py` survivors are materially lower than the current 124. Completed:
  124 to 39, zero suspicious/timeouts.
- `doctor/cli.py` either has fewer survivors than the current 270 or a
  documented refactor plan based on survivor clusters. Completed: 270 to 11
  after extracting environment, integration, and output support modules, zero
  suspicious/timeouts.
- No raw Mutmut logs are committed.
- No advisory target is added to blocking `[tool.mutmut].only_mutate` unless it
  is near the current blocking policy.
- Manual profile still passes with `mutmut_max_survivors = 16` and
  `mutmut_min_score = 94`.

## Verification

```bash
python3 -m agent_maintainer guidance --check
python3 -m agent_maintainer change-plan check
tach check --exact
python3 -m agent_maintainer verify --profile precommit
python3 -m agent_maintainer verify --profile full
python3 -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
python3 -m agent_maintainer verify --profile security
python3 -m agent_maintainer verify --profile manual
```
