# TypeScript LCOV Changed-Line Facts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task by task.

**Goal:** Add a bounded advisory report that combines existing TypeScript LCOV
artifacts with executable lines changed in a selected Git diff.

**Architecture:** `agent_repair_facts` owns generic LCOV record parsing.
`agent_maintainer.test_intel` owns repository confinement, TypeScript source
classification, Git changed-line mapping, weighted aggregation, CLI handling,
and rendering. The report is explicit and advisory; no provider check, runner,
threshold, or blocking gate is added.

**Tech Stack:** Python 3.11+, dataclasses, pathlib, subprocess, argparse, pytest,
Ruff, Wemake/flake8, Pyright, Tach, Archguard, DocSync, Markdownlint, LCOV.

## Global Constraints

- Keep TypeScript/JavaScript experimental and the new report advisory.
- Do not run or infer Vitest, Jest, Istanbul, V8, npm, pnpm, Yarn, or Bun.
- Do not call `diff-cover`, add a threshold, alter verifier profiles, or change
  process exit status based on coverage percentage.
- Default only the input artifact path to `coverage/lcov.info`; allow explicit
  `--lcov`, `--source-root`, `--base-ref`, `--staged`, and `--format` options.
- Confine the LCOV artifact and source root to the repository after symlink
  resolution.
- Include only non-deleted paths classified as TypeScript/JavaScript source.
- Match LCOV sources conservatively; do not guess workspace or source prefixes.
- Compute one weighted percentage from total executable changed lines.
- Keep missing artifact evidence separate from uncovered executable evidence.
- Bound input at 10 MiB, normalized paths at 500 characters, retained file
  facts at 500, and rendered text details at 50 total lines.
- Use synthetic fixtures as the normative contract and pinned public
  projections only as offline compatibility evidence.
- Preserve existing TypeScript artifact repair facts and Python test-intel
  coverage behavior.
- Base the draft PR on `codex/typescript-dependency-cruiser-facts` until Phase
  181 PR #400 lands.

---

## Task 1: Expose reusable LCOV line records

**Files:**

- Modify: `src/agent_repair_facts/parsers/typescript_coverage.py`
- Modify: `src/agent_repair_facts/tach.domain.toml` only if a new dependency is
  actually required
- Create: `tests/repair_facts/test_typescript_lcov_records.py`
- Verify: `tests/core/test_typescript_structured_output.py`
- Verify: `tests/context/test_typescript_exact_facts.py`

**Interfaces:**

- Add immutable `LcovFileRecord` with `source`, `executable_lines`, and
  `covered_lines`.
- Add `parse_lcov_records(raw_output: str) -> tuple[LcovFileRecord, ...]`.
- Refactor `parse_lcov_info` to render missing-line diagnostics from those
  records without changing its public fact shape.

- [ ] **Step 1: Write failing record-parser tests**

Cover:

- one source with positive, zero, and negative hit counts;
- malformed `DA` neighbors that are ignored independently;
- an unterminated final record;
- duplicate `SF` records and duplicate lines where any positive hit wins;
- deterministic source/line ordering;
- empty, dot, control-bearing, and overlong source values skipped;
- records without `DA` lines retained so artifact presence remains distinct
  from executable-line presence.

Run:

```bash
PATH=.venv/bin:$PATH pytest tests/repair_facts/test_typescript_lcov_records.py -q
```

Expected: FAIL because the record model and parser do not exist.

- [ ] **Step 2: Implement the smallest reusable parser**

Parse only `SF:`, `DA:`, and `end_of_record`. Keep a per-source executable set
and covered set, merge exact duplicate source names, sort before freezing, and
cap source input before returning records. A positive line number is executable;
hits greater than zero mark coverage. Negative or zero hits remain missing.

Do not normalize repository paths in this package. It has no repository root,
workspace root, Git, or orchestration knowledge.

- [ ] **Step 3: Preserve existing LCOV repair facts**

Refactor `parse_lcov_info` to calculate missing lines as
`executable_lines - covered_lines`. Run:

```bash
PATH=.venv/bin:$PATH pytest \
  tests/repair_facts/test_typescript_lcov_records.py \
  tests/core/test_typescript_structured_output.py \
  tests/context/test_typescript_exact_facts.py -q
```

Expected: PASS with the existing `typescript-coverage` diagnostic contract
unchanged.

- [ ] **Step 4: Commit the parser slice**

```bash
git add -- \
  src/agent_repair_facts/parsers/typescript_coverage.py \
  tests/repair_facts/test_typescript_lcov_records.py
git commit -m "feat: expose reusable TypeScript LCOV records"
```

Include the Tach file only if its dependency declarations changed.

## Task 2: Build the Git-aware TypeScript coverage adapter

**Files:**

- Create: `src/agent_maintainer/test_intel/typescript_coverage.py`
- Modify: `src/agent_maintainer/test_intel/tach.domain.toml`
- Create: `docs/architecture/decisions/2026-07-17-typescript-lcov-changed-line-boundary.md`
- Create: `tests/test_intel/test_typescript_coverage.py`

**Interfaces:**

- `TypeScriptCoverageFileFact`: path plus executable/covered/missed changed-line
  counts and an optional percentage.
- `TypeScriptCoverageReport`: artifact/base metadata, changed sources,
  missing-from-LCOV paths, aggregate counts/percentage, total matched files,
  retained file facts, and the advisory note.
- `build_report(request: TypeScriptCoverageRequest) -> TypeScriptCoverageReport`.
- A small report-specific exception for user-actionable path, artifact, Git, or
  LCOV failures.

- [ ] **Step 1: Write failing path-confinement tests**

Cover repository-relative and absolute paths inside the repository, workspace
relative `SF:src/app.ts` with `source_root=packages/web`, absolute in-repository
`SF` paths, `./` and backslash normalization, symlinks escaping the repository,
parent traversal, foreign absolute paths, Windows drive paths, controls, dot,
empty, and overlong values.

The artifact and source root must both resolve within the repository. Artifact
reads reject non-files, invalid UTF-8, and files larger than 10 MiB.

Run:

```bash
PATH=.venv/bin:$PATH pytest tests/test_intel/test_typescript_coverage.py -q
```

Expected: FAIL because the adapter does not exist.

- [ ] **Step 2: Implement bounded LCOV loading and normalization**

Use `Path.resolve()` and `Path.is_relative_to()` only after validating the
repository root. Render all accepted paths repository-relative and POSIX-style.
Never place local absolute roots in models or errors. Merge records again after
normalization because distinct raw `SF` values can resolve to one file.

- [ ] **Step 3: Write failing changed-source discovery tests**

Create temporary Git repositories and assert that the selected diff includes
added, copied, renamed, and modified `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, and
`.cjs` source files. Exclude deleted files, test/spec paths, generated markers,
ignored build/tool directories, config, docs, lockfiles, and non-TypeScript
files. Cover unstaged and staged modes plus an invalid base ref.

- [ ] **Step 4: Implement changed-source discovery**

Run a zero-side-effect `git diff --name-only` from the explicit repository root
with copy/rename detection and an `ACMR` diff filter. Classify each result with
`ecosystems.typescript.classification.classify_path` and retain `FileRole.SOURCE`
only. Raise the report-specific error on Git failure.

- [ ] **Step 5: Write failing weighted-coverage tests**

Cover:

- two files whose weighted result differs from an average of file percentages;
- changed comments/blanks absent from `DA` excluded from the denominator;
- duplicate records and lines counted once;
- changed source absent from LCOV listed in `missing_from_lcov`;
- a matching record with no executable changed lines producing `None`, not
  `0.0` or `100.0`;
- no changed TypeScript source;
- at least one usable LCOV line required for an explicitly invoked report;
- deterministic sorting and 500-file retention with truthful total count.

- [ ] **Step 6: Implement report composition**

Reuse `coverage_lines.changed_line_numbers`; do not duplicate diff-hunk parsing.
Calculate each file's executable set intersection and aggregate integer counts
before rounding one final percentage to two decimals. Report paths missing from
the normalized LCOV map separately and exclude them from the denominator.

- [ ] **Step 7: Record and verify the architecture boundary**

The ADR must state:

- generic LCOV syntax/line records belong to `agent_repair_facts`;
- repository confinement, TypeScript classification, Git diffs, percentage
  math, and rendering belong to `agent_maintainer.test_intel`;
- `agent_repair_facts` must not import `agent_maintainer`;
- this report does not replace Python `diff-cover` or add a verifier gate.

Update `test_intel/tach.domain.toml` with only the exact dependencies used by
the new module. Run:

```bash
PATH=.venv/bin:$PATH pytest tests/test_intel/test_typescript_coverage.py -q
PATH=.venv/bin:$PATH python -m tach check
PATH=.venv/bin:$PATH python -m agent_maintainer architecture check
```

Expected: PASS.

- [ ] **Step 8: Commit the adapter slice**

```bash
git add -- \
  src/agent_maintainer/test_intel/typescript_coverage.py \
  src/agent_maintainer/test_intel/tach.domain.toml \
  docs/architecture/decisions/2026-07-17-typescript-lcov-changed-line-boundary.md \
  tests/test_intel/test_typescript_coverage.py
git commit -m "feat: calculate TypeScript changed-line coverage"
```

## Task 3: Add bounded text and JSON CLI output

**Files:**

- Create: `src/agent_maintainer/test_intel/typescript_coverage_reporting.py`
- Create: `src/agent_maintainer/test_intel/typescript_coverage_cli.py`
- Modify: `src/agent_maintainer/test_intel/cli.py`
- Modify: `src/agent_maintainer/test_intel/tach.domain.toml`
- Create: `tests/test_intel/test_typescript_coverage_cli.py`

- [ ] **Step 1: Write failing renderer tests**

Require stable sorted JSON keys and values, aggregate-first text, per-file
counts, missing-artifact paths, explicit advisory language, unknown coverage
when the denominator is zero, 50 total detail lines, and a truthful omission
marker.

- [ ] **Step 2: Implement renderers**

Keep models serializable through explicit `to_json()` methods. JSON retains the
500 sorted file facts; text renders at most 50 combined file/missing details.
Neither format includes raw LCOV or local absolute paths.

- [ ] **Step 3: Write failing CLI tests**

Assert defaults and explicit options for:

```text
test-intel typescript-coverage
  --lcov PATH
  --source-root PATH
  --base-ref REF
  --staged
  --format text|json
```

Verify exit 0 for valid reports regardless of percentage and exit 1 with a
concise stderr error for missing/unsafe/oversized/malformed artifacts, unsafe
source roots, and invalid Git refs.

- [ ] **Step 4: Register and implement the CLI adapter**

Follow the mutation subcommand pattern: the dedicated CLI module owns parser
arguments and error handling; the top-level `test_intel.cli` registers and
dispatches it. Resolve the current working directory as repository root.

- [ ] **Step 5: Run the focused command suite**

```bash
PATH=.venv/bin:$PATH pytest \
  tests/test_intel/test_typescript_coverage.py \
  tests/test_intel/test_typescript_coverage_cli.py \
  tests/test_intel/test_changed.py \
  tests/test_intel/test_reporting.py -q
PATH=.venv/bin:$PATH python -m tach check
```

Expected: PASS.

- [ ] **Step 6: Commit the CLI slice**

```bash
git add -- \
  src/agent_maintainer/test_intel/typescript_coverage_reporting.py \
  src/agent_maintainer/test_intel/typescript_coverage_cli.py \
  src/agent_maintainer/test_intel/cli.py \
  src/agent_maintainer/test_intel/tach.domain.toml \
  tests/test_intel/test_typescript_coverage_cli.py
git commit -m "feat: report advisory TypeScript diff coverage"
```

## Task 4: Add public compatibility evidence and user documentation

**Files:**

- Create: `tests/fixtures/typescript_lcov_external/README.md`
- Create: two bounded JSON/LCOV projections beneath
  `tests/fixtures/typescript_lcov_external/`
- Create: `tests/assess/test_typescript_lcov_external_fixtures.py`
- Create: `docs/roadmap/phases/phase-182-typescript-lcov-changed-line-facts.md`
- Modify: `docs/roadmap/typescript-react-parity-roadmap.md`
- Modify: `docs/typescript-javascript-provider.md`
- Modify: `docs/provider-status.md`
- Modify: `docs/test-intelligence.md`
- Modify: DocSync trace/attestation only when required by changed claims

- [ ] **Step 1: Capture two pinned public projections**

Use the research-selected repositories only after verifying their pinned
commits and public LCOV shape. Record repository URL, full commit, UTC
collection time, package manager and lockfile, Node and coverage-tool versions,
the upstream coverage command/configuration, raw artifact SHA-256 and size, and
the bounded normalized records needed for offline replay.

Do not commit repository source, private paths, dependency trees, arbitrary
command output, or an unbounded LCOV report. Do not execute package lifecycle
scripts merely to generate evidence when a public committed/CI artifact or
bounded upstream projection suffices.

- [ ] **Step 2: Write replay and provenance tests**

Assert the complete provenance schema, full commit/hash formats, parseability,
safe repository-relative sources, two distinct project/package shapes, exact
weighted counts, deterministic output, and absence of local absolute paths or
private data.

- [ ] **Step 3: Update public docs and roadmap order**

Document the exact command, workspace `--source-root` example, advisory
semantics, weighted executable changed-line denominator, missing artifact
behavior, and distinction from Python blocking `diff-cover`.

Reorder the remaining roadmap exactly as approved:

1. Phase 182 LCOV changed-line facts — complete;
2. package-manager audit facts;
3. generated-file/framework policy;
4. blocking reviewability promotion assessment;
5. declared Nx boundaries;
6. React hooks/accessibility/Testing Library recommendations;
7. StrykerJS mutation facts.

Keep broader security work visible in the roadmap without silently pulling it
into this ordered implementation slice.

- [ ] **Step 4: Verify docs and evidence**

```bash
PATH=.venv/bin:$PATH pytest \
  tests/assess/test_typescript_lcov_external_fixtures.py \
  tests/docs/test_first_touch_docs.py \
  tests/docsync/test_public_doc_trace.py -q
PATH=.venv/bin:$PATH python -m docsync check
```

If DocSync requests attestation, add only a fresh human-authored attestation
after the evidence and claim are final.

- [ ] **Step 5: Commit the evidence/docs slice**

Stage the exact files changed and commit:

```bash
git commit -m "docs: complete TypeScript LCOV facts phase"
```

## Task 5: Full validation, independent review, and publication

- [ ] **Step 1: Run focused quality gates**

```bash
PATH=.venv/bin:$PATH pytest \
  tests/repair_facts/test_typescript_lcov_records.py \
  tests/test_intel/test_typescript_coverage.py \
  tests/test_intel/test_typescript_coverage_cli.py \
  tests/assess/test_typescript_lcov_external_fixtures.py \
  tests/core/test_typescript_structured_output.py \
  tests/context/test_typescript_exact_facts.py -q
PATH=.venv/bin:$PATH ruff check \
  src/agent_repair_facts/parsers/typescript_coverage.py \
  src/agent_maintainer/test_intel/typescript_coverage.py \
  src/agent_maintainer/test_intel/typescript_coverage_cli.py \
  src/agent_maintainer/test_intel/typescript_coverage_reporting.py \
  tests/repair_facts/test_typescript_lcov_records.py \
  tests/test_intel/test_typescript_coverage.py \
  tests/test_intel/test_typescript_coverage_cli.py
PATH=.venv/bin:$PATH pyright \
  src/agent_repair_facts/parsers/typescript_coverage.py \
  src/agent_maintainer/test_intel/typescript_coverage.py \
  src/agent_maintainer/test_intel/typescript_coverage_cli.py \
  src/agent_maintainer/test_intel/typescript_coverage_reporting.py
PATH=.venv/bin:$PATH python -m tach check
PATH=.venv/bin:$PATH python -m agent_maintainer architecture check
PATH=.venv/bin:$PATH python -m docsync check
```

- [ ] **Step 2: Run the full verifier**

```bash
PATH=.venv/bin:$PATH python -m agent_maintainer verify --profile full
```

Require a fresh PASS run ID. Do not claim completion from focused tests alone.

- [ ] **Step 3: Request one comprehensive independent review**

Review the complete diff against the approved design, emphasizing path
confinement/symlink safety, malformed and duplicate LCOV semantics, Git diff
selection, weighted math, bounds, public provenance, architecture direction,
and accidental enforcement. Fix important findings and rerun the smallest
relevant gates plus the full verifier when behavior changes.

- [ ] **Step 4: Final safety review**

Inspect `git status --short --branch`, diff stat, actual diff, staged state,
recent commits, and fixtures/attestations for secrets, credentials, private
paths, or generated residue. The worktree must be intentionally clean.

- [ ] **Step 5: Push and open a stacked draft PR**

Push `codex/typescript-lcov-diff-facts` and create a draft PR whose base is
`codex/typescript-dependency-cruiser-facts` while PR #400 is open. Include the
design decisions, commands/checks, full verifier run ID, external evidence,
advisory-only boundary, and stack dependency. Watch all hosted checks to a
terminal state and repair any failures before handoff.
