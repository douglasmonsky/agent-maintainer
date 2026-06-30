# Phase 39: Coverage Semantics Hardening

## PR Title

```text
fix: clarify changed coverage semantics
```

## Goal

Remove ambiguity in test-intelligence coverage output. If a value represents
coverage of files touched by a change, name it accordingly. If changed-line
coverage is exposed, compute it by intersecting changed diff hunks with
coverage line data.

## Requirements

- Audit current `changed_coverage` fields and docs.
- Rename existing file-average semantics to `changed_source_file_coverage`, or
  implement real `changed_line_coverage` and expose both separately.
- Keep CLI text clear enough that agents do not confuse file coverage with
  changed-line coverage.
- Update tests and docs for the new field names.

## Out Of Scope

- Do not replace `diff-cover` as the blocking changed-code coverage gate.
- Do not invent branch coverage semantics unless existing artifacts support it.

## Acceptance Criteria

- Test-intelligence JSON/text output names coverage semantics accurately.
- Tests prove XML/JSON coverage parsing produces the documented field.
- Precommit and focused test-intelligence tests pass.

---
