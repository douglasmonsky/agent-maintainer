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

## Planned Next Layers

Planned capabilities include smarter source-without-test guidance, branch
coverage signals, mutation-test target suggestions, Hypothesis candidate
guidance, and CrossHair candidate guidance for pure typed functions.

These signals should guide better tests without encouraging coverage theater or
turning slow research tools into normal precommit gates.
