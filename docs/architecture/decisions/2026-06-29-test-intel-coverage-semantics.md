# Architecture Decision: Test-Intelligence Coverage Semantics

Status: accepted

## Context

The test-intelligence changed report exposed `changed_line_coverage`, but the
implementation averaged whole-file coverage for changed source files. That made
the advisory output easy to confuse with the blocking `diff-cover` changed-line
coverage gate.

## Decision

Expose two separate coverage signals:

- `changed_source_file_coverage` for the existing average whole-file coverage
  of changed source files.
- `changed_line_coverage` for executable lines that are both changed in the Git
  diff and present in coverage artifacts.

Move Git diff hunk parsing into `agent_maintainer.test_intel.coverage_lines`.
`coverage.py` remains responsible for reading coverage artifacts and combining
artifact line data with the changed-line map.

## Alternatives Considered

Renaming the old field without implementing changed-line coverage was rejected
because the JSON API already used the stronger name.

Making test intelligence call `diff-cover` was rejected because `diff-cover`
already runs as the blocking verifier gate. Test intelligence should expose
advisory repair hints without replacing verifier enforcement.

## Still Forbidden

The test-intelligence coverage report remains advisory. It must not replace the
normal coverage or `diff-cover` verifier gates.
