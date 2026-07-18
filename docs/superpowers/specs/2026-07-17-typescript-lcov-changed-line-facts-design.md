# TypeScript LCOV Changed-Line Facts Design

**Date:** 2026-07-17
**Status:** Approved through the recorded recommended-choice workflow
**Phase:** 182

## Context

Agent Maintainer already parses Istanbul/V8 LCOV artifacts into bounded
TypeScript repair facts, and its advisory Python test-intelligence report
already maps Git diff hunks to executable coverage lines. The TypeScript parity
roadmap calls for combining those capabilities before considering any coverage
threshold or blocking provider promotion.

The user selected LCOV changed-line coverage as the highest-impact remaining
TypeScript item and approved this order for the remaining roadmap: LCOV facts,
package-manager audit facts, generated-file/framework policy, blocking
promotion assessment, then lower-priority Nx/React-lint/Stryker work.

## Decision

Add a dedicated advisory command:

```console
python -m agent_maintainer test-intel typescript-coverage \
  --lcov coverage/lcov.info \
  --base-ref HEAD
```

The command reads an existing LCOV artifact, identifies changed
TypeScript/JavaScript source lines from the selected Git diff, and reports a
weighted aggregate plus bounded per-file facts. It never runs a test runner,
adds reporter flags, infers a package manager, or enforces a threshold.

Generic LCOV record parsing stays in `agent_repair_facts`. The orchestration
adapter, Git integration, models, and rendering stay in
`agent_maintainer.test_intel`. This preserves the internal package dependency
direction and reuses the existing `coverage_lines` diff parser.

## Recorded Self-Approved Choices

The user previously asked that each remaining choice be recorded while the
recommended answer proceeds automatically. These are the Phase 182 choices.

1. **Public surface?** Use a dedicated `test-intel typescript-coverage`
   command. Extending `test-intel changed` would mix a Python-only test mapper
   with a TypeScript-only artifact contract.
2. **Artifact ownership?** Require an existing LCOV path, defaulting only to
   the conventional `coverage/lcov.info`. Do not run or infer a coverage
   command.
3. **Workspace mapping?** Add explicit `--source-root`, defaulting to the
   repository root. Relative `SF:` paths resolve beneath that root; absolute
   paths are accepted only when they resolve inside the repository.
4. **Changed source discovery?** Use Git diff paths classified by the existing
   TypeScript/JavaScript provider. Include source roles only; exclude tests,
   generated files, ignored outputs, configuration, docs, and lockfiles.
5. **Coverage math?** Divide total covered executable changed lines by total
   executable changed lines across all matched files. Do not average per-file
   percentages.
6. **Fact shape?** Return aggregate counts/percentage and deterministic
   per-file facts. Keep existing artifact-only missing-line repair facts
   unchanged.
7. **No executable changed lines?** Return a successful advisory report with
   an unknown percentage and a clear note, not a synthetic 0% or 100%.
8. **Malformed or missing input?** Exit nonzero with a concise error because
   the user explicitly invoked this report. Normal verifier artifact parsing
   retains its existing bounded fallback behavior.
9. **Duplicate LCOV records?** Merge executable lines by path; a line is
   covered when any matching `DA` record has positive hits, and missing only
   when all matching records report zero hits.
10. **Enforcement?** Add no threshold, ratchet, baseline, profile check, or
    exit-status change based on the percentage. Promotion remains a later
    evidence-backed decision.
11. **External evidence?** Replay bounded projections from pinned public
    TypeScript repositories offline; synthetic fixtures remain the normative
    contract.
12. **Roadmap order?** Record LCOV as Phase 182, then package-manager audit,
    generated-file/framework policy, blocking promotion assessment, declared
    Nx, React lint recommendations, and Stryker.

## Approaches Considered

### Dedicated advisory LCOV report — selected

This gives the artifact, Git base, staging mode, and workspace source root an
explicit contract. It can evolve without widening the Python likely-test
mapper or the verifier gate surface.

### Extend `test-intel changed` — rejected

That report discovers only configured Python source and maps only pytest files.
Teaching it TypeScript coverage without TypeScript test mapping would create a
misleading mixed report and broaden a stable JSON contract.

### Invoke `diff-cover` or a JavaScript runner — rejected

`diff-cover` remains the Python blocking verifier backend. Calling it from
TypeScript advisory reporting would blur enforcement semantics, while invoking
Vitest/Jest/npm/pnpm would violate explicit command ownership and introduce
runner/version inference.

## CLI Contract

```text
test-intel typescript-coverage
  --lcov PATH             default: coverage/lcov.info
  --source-root PATH      default: .
  --base-ref REF          default: HEAD
  --staged
  --format text|json      default: text
```

`--source-root` may be repository-relative or absolute, but its resolved value
must be the repository root or a descendant. The LCOV file may be outside the
source root but must be a regular readable file within the repository. This
keeps the report scoped to repository-owned artifacts and avoids accidental
private-file reads.

Git failures, an invalid base ref, an unsafe source root or artifact path, an
oversized artifact, and a structurally unusable LCOV input produce exit 1.
Valid reports produce exit 0 regardless of coverage percentage.

## LCOV Input Contract

The reusable parser recognizes standard records:

```text
SF:src/widget.ts
DA:10,1
DA:11,0
end_of_record
```

Only `SF`, `DA`, and `end_of_record` affect Phase 182. Branch, function, and
summary records remain out of scope. A usable artifact contains at least one
safe source record and one valid positive line-number `DA` entry. Malformed
records are skipped independently; if no usable coverage lines remain, the
explicit command reports an error.

The parser returns immutable per-source line-hit records without importing Git,
configuration, or `agent_maintainer`. Existing LCOV diagnostic rendering uses
the same parsed records so duplicate and malformed-line semantics stay aligned.

## Path And Workspace Contract

Path handling is conservative and deterministic:

- Normalize separators and remove leading `./` from relative `SF:` values.
- Resolve relative `SF:` paths beneath the explicit source root.
- Resolve absolute `SF:` paths directly, but retain them only when they are
  inside the repository.
- Reject parent traversal outside the repository, drive-qualified paths that
  cannot be proven local, control-bearing paths, empty/dot paths, and paths
  longer than 500 characters.
- Convert accepted paths to repository-relative POSIX form before matching Git
  paths or rendering JSON.
- Do not guess missing workspace prefixes or source directories.

For a workspace-produced artifact whose records contain `SF:src/app.ts`, the
caller supplies `--source-root packages/web`. Root-produced records such as
`SF:packages/web/src/app.ts` use the default source root.

## Changed-Line And Coverage Semantics

The adapter obtains changed paths from the same Git diff modes already used by
test intelligence: unstaged worktree changes against `--base-ref`, or staged
changes when `--staged` is selected. It then reuses
`coverage_lines.changed_line_numbers` for zero-context hunk parsing.

For each matched source:

```text
executable_changed = changed_lines ∩ LCOV_DA_lines
covered_changed = executable_changed ∩ positive_hit_lines
missed_changed = executable_changed - covered_changed
```

The aggregate percentage is:

```text
100 * sum(covered_changed) / sum(executable_changed)
```

Each executable line is counted once after duplicate-record merging. Changed
comments, blanks, type-only declarations without `DA` entries, and files absent
from LCOV do not enter the denominator. The report separately names changed
source files missing from the artifact so missing evidence is visible without
being misrepresented as uncovered executable code.

## Output Contract

The JSON report contains stable keys:

- `artifact_path`, `source_root`, `base_ref`, and `staged`;
- `changed_source` and `missing_from_lcov`;
- `executable_changed_lines`, `covered_changed_lines`, and
  `missed_changed_lines`;
- `changed_line_coverage` as a two-decimal float or `null`;
- `files`, a deterministic array of matched per-file count/percentage facts;
- `note`, explicitly stating that the report is advisory.

Text output renders the aggregate first, then at most 50 per-file or missing
artifact lines with a truthful omission marker. JSON retains at most 500 file
facts after sorting and reports the total matched count before retention.

## Bounds And Failure Safety

- Read at most 10 MiB of LCOV text after checking regular-file size.
- Bound individual decoded lines and source values to 1,000 characters before
  normalization; source paths remain subject to the 500-character target bound.
- Retain at most 500 normalized file facts after deterministic sorting.
- Render at most 50 total text detail lines.
- Do not include raw LCOV text, local absolute roots, environment variables, or
  source contents in the report.
- Catch file, decode, path-resolution, Git, and parser errors at the CLI
  boundary and return a concise user-facing error.

## Architecture And Documentation

Add a focused architecture decision recording that reusable LCOV records live
in `agent_repair_facts`, while Git-aware advisory composition lives in
`test_intel`. Update Tach declarations for the explicit new modules only.

Update the TypeScript provider guide, provider-status table, test-intelligence
guide, roadmap, and Phase 182 card. TypeScript/JavaScript remains experimental,
and docs must distinguish this report from blocking changed-line coverage.

## Verification And Evidence

Use TDD for parser, path normalization, weighted math, CLI rendering, and
failure behavior. Synthetic tests cover root and workspace paths, duplicate
records, missing files, no executable changed lines, unsafe paths, malformed
neighbors, oversized inputs, staged diffs, and deterministic bounds.

Public projections record repository URL, full pinned commit, UTC collection
time, package-manager/lockfile evidence, Node and coverage-tool versions, exact
coverage command from upstream CI/configuration, artifact hash/size, and
normalized aggregate counts. Tests replay only the bounded public LCOV
projection and never depend on network access or execute repository scripts.

Before publication, run focused tests, architecture and documentation checks,
the full verifier, an independent review, and hosted CI on a stacked draft pull
request based on Phase 181 until its parent lands.

## Success Criteria

- A root or workspace LCOV artifact yields exact weighted changed-line counts
  for changed TypeScript/JavaScript source.
- Unsafe or ambiguous paths never match repository files.
- Missing coverage evidence is visible but never silently counted as uncovered.
- JSON and text output are bounded, deterministic, and explicitly advisory.
- Existing TypeScript repair facts and Python coverage/diff-cover behavior stay
  compatible.
- No coverage command, package manager, threshold, or blocking gate is added.
