<!-- docsync:object docs.test_intelligence.overview -->
# Test Intelligence

Test intelligence helps agents choose meaningful tests when source changes. It
does not replace pytest, coverage, or diff-cover gates. It gives deterministic
hints about which tests are likely relevant so repair loops can start with a
focused command instead of guessing.

## Changed-Source MVP

Run:

```bash
python -m agent_maintainer test-intel changed
python -m agent_maintainer test-intel changed --base-ref origin/main
python -m agent_maintainer test-intel changed --staged
python -m agent_maintainer test-intel changed --format json
```

The command reads configured `source_roots` and `test_roots`, asks Git for
changed Python source files, scans pytest-style test files, and ranks likely
tests with stable confidence labels.

Signals:

- `high`: test filename matches or imports the changed module.
- `medium`: test filename roughly matches or imports the changed module.
- `low`: test lives in the same package/domain folder.

Output includes changed source files, likely test files, reasons, coverage
metadata when `coverage.json` or `coverage.xml` is present, and suggested
focused pytest commands.

Coverage output separates two advisory signals:

- `changed_source_file_coverage`: average whole-file coverage for changed
  source files.
- `changed_line_coverage`: coverage for executable lines changed in the Git
  diff when coverage artifacts are present.

The blocking changed-code coverage gate remains `diff-cover`; test intelligence
reports values only to help agents pick focused repair commands. Change-budget
warnings use the same mapping so source changes do not ignore likely relevant
test changes. The warning stays non-blocking unless existing strict
warning-as-error options are enabled.

## Hypothesis Candidate Guidance

Run:

```bash
python -m agent_maintainer test-intel hypothesis-candidates
python -m agent_maintainer test-intel hypothesis-candidates --changed
python -m agent_maintainer test-intel hypothesis-candidates --format json
```

The command scans configured source roots and ranks functions that look like
good property-test candidates: typed functions, branchy decision logic,
pure-ish parsers, validators, normalizers, and numeric or string boundary
behavior.

Output is advisory only. Suggested scaffolds are starting points, not verified
contracts. The command does not import Hypothesis, run tests, or modify files.

## Mutation Target Suggestions

Run:

```bash
python -m agent_maintainer test-intel mutation-targets
python -m agent_maintainer test-intel mutation-targets --changed
python -m agent_maintainer test-intel mutation-targets --ratchet
python -m agent_maintainer test-intel mutation-targets --format json
```

The command ranks functions that look useful for manual mutation testing:
changed source, likely focused test coverage, ratchet hotspots, branchy
pure-ish logic, parser/validator/decision names.

Output is advisory only. The command does not run Mutmut and does not make
mutation testing a normal precommit gate. Repositories own targeted
`[tool.mutmut].only_mutate` lists, and
`[tool.agent_maintainer].mutmut_target_min` ratchets the configured target
count. The ratchet runs in `full` and `ci` because it only validates
configuration shape, supported Mutmut keys, path-like target existence, and
concrete `also_copy` / `do_not_mutate` paths; actual Mutmut execution stays in
`manual`.

Agent Maintainer intentionally rejects unsupported Mutmut keys rather than
letting the pinned Mutmut version ignore them silently.

## Mutation Results

Run:

```bash
python -m agent_maintainer test-intel mutation-results
python -m agent_maintainer test-intel mutation-results --format json
python -m agent_maintainer test-intel mutation-results --path mutants/mutmut-cicd-stats.json
```

The command reads Mutmut's exported CI/CD stats and summarizes killed,
survived, suspicious, and timed-out mutants. It prefers live
`mutants/mutmut-cicd-stats.json`, then falls back to retained run or mutation
sweep artifacts under `.verify-logs/` after successful cleanup. It does not run
Mutmut.

Repositories can enable
`[tool.agent_maintainer].mutmut_result_ratchet_enabled` to make the manual
Mutmut gate fail when survivor, suspicious, timeout, or mutation score budgets
regress. This repo currently dogfoods the ratchet against a measured targeted
baseline.

## Mutation Sweep

Run:

```bash
python -m agent_maintainer test-intel mutation-sweep
python -m agent_maintainer test-intel mutation-sweep --changed
python -m agent_maintainer test-intel mutation-sweep --execute
python -m agent_maintainer test-intel mutation-sweep --execute --candidate-limit 2
python -m agent_maintainer test-intel mutation-sweep --format json
```

The sweep planner ranks module-level mutation targets using changed files,
likely focused tests, coverage artifacts, branch complexity, recent Git churn,
and ratchet hotspots. Planner mode is advisory and does not run Mutmut. Because
Mutmut targeting is config-driven, each candidate recommends a
`[tool.mutmut].only_mutate` promotion plus the manual verification command to
run after a config update.

`--execute` is still advisory, but it runs selected ranked candidates safely in
copied temporary worktrees. The temp copy receives the candidate `only_mutate`
target and likely focused tests; the source checkout's `pyproject.toml` is not
modified. Raw Mutmut logs and exported stats live under
`.verify-logs/mutation-sweeps/<run-id>/`, while terminal output stays compact.

Keep blocking mutation testing targeted and ratcheted in `manual`; broad sweeps
remain release/manual research until runtime and signal quality are stable.

## CrossHair Candidate Guidance

Run:

```bash
python -m agent_maintainer test-intel crosshair-candidates
python -m agent_maintainer test-intel crosshair-candidates --changed
python -m agent_maintainer test-intel crosshair-candidates --format json
```

The command suggests functions that are likely safer manual CrossHair targets:
fully typed public functions, visible `assert`, docstring, `icontract`, or
`deal` contracts, small bounded bodies, and no obvious filesystem, network,
subprocess, or database access.

Output is advisory only. The command does not run CrossHair and does not make
formal analysis a normal precommit gate.

## Planned Next Layers

Planned capabilities include smarter source-without-test guidance, branch
coverage signals, and richer repair planning for larger changes. These signals
should guide better tests without encouraging coverage theater or turning slow
research tools into normal precommit gates.
<!-- docsync:object.end docs.test_intelligence.overview -->
