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

- `high`: test filename matches and imports the changed module.
- `medium`: test filename matches or imports the changed module.
- `low`: test lives in the same package/domain folder.

Output includes changed source files, likely test files, reasons, coverage
metadata when `coverage.json` or `coverage.xml` is present, and suggested
focused pytest commands.

Change-budget warnings use this same mapping when source changes do not include
likely relevant test changes. The warning stays non-blocking unless existing
strict warning-as-error options are enabled.

## Hypothesis Candidate Guidance

Run:

```bash
python -m agent_maintainer test-intel hypothesis-candidates
python -m agent_maintainer test-intel hypothesis-candidates --changed
python -m agent_maintainer test-intel hypothesis-candidates --format json
```

The command scans configured source roots and ranks functions that look like good
property-test candidates: typed functions, branchy decision logic, pure-ish
parsers, validators, normalizers, and numeric or string boundary behavior.

Output is advisory only. Suggested scaffolds are starting points, not verified
contracts, and the command does not import Hypothesis, run tests, or modify
files.

## Mutation Target Suggestions

Run:

```bash
python -m agent_maintainer test-intel mutation-targets
python -m agent_maintainer test-intel mutation-targets --changed
python -m agent_maintainer test-intel mutation-targets --ratchet
python -m agent_maintainer test-intel mutation-targets --format json
```

The command ranks functions that look useful for manual mutation testing:
changed source, likely focused test coverage, ratchet hotspots, branchy pure-ish
logic, and parser/validator/decision names.

Output is advisory only. The command does not run Mutmut and does not make
mutation testing a normal precommit gate.

## CrossHair Candidate Guidance

Run:

```bash
python -m agent_maintainer test-intel crosshair-candidates
python -m agent_maintainer test-intel crosshair-candidates --changed
python -m agent_maintainer test-intel crosshair-candidates --format json
```

The command suggests functions that are likely safer manual CrossHair targets:
fully typed public functions with visible `assert`, docstring, `icontract`, or
`deal` contracts, small bounded bodies, and no obvious filesystem, network,
subprocess, or database access.

Output is advisory only. The command does not run CrossHair and does not make
formal analysis a normal precommit gate.

## Planned Next Layers

Planned capabilities include smarter source-without-test guidance, branch
coverage signals and richer repair planning for larger changes.

These signals should guide better tests without encouraging coverage theater or
turning slow research tools into normal precommit gates.
