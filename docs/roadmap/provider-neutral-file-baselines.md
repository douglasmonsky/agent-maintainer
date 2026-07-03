# Provider-Neutral File Baseline Controls

Agent Maintainer should support broad file policy controls without pretending
every ecosystem has the same architecture, test, coverage, or suppression
model. The right abstraction is a provider-neutral file baseline layer for
simple file facts, plus provider-owned adapters for ecosystem semantics.

## Motivation

Several current reviewability checks are globally scheduled but still
Python-backed: file length, change budget, structure cohesion, suppression
budget, and source-without-test checks. That is correct for the current
implementation, but it is too narrow for mixed repositories. Many useful
controls can apply safely across file types before TypeScript, JavaScript, Go,
or other ecosystems become blocking providers.

Examples:

- maximum physical lines per file;
- maximum source/nonblank lines per file;
- maximum added/deleted lines per file group;
- maximum changed files per file group;
- generated/ignored path handling;
- large-file and duplicate-artifact hygiene;
- advisory source/test/config/dependency spread summaries;
- broad suppression scanning where a provider supplies markers.

These controls should work from path and filetype rules where that is enough.
They should not require a language-specific import graph.

## Tach Boundary

Tach is not the cross-language architecture answer. In this repository it
enforces Python module/import contracts under configured `source_roots` with
`root_module = "forbid"`. It is valuable for Python architecture boundaries,
but it does not understand TypeScript, JavaScript, Go, Rust, Java, or other
language import graphs.

Agent Maintainer should keep using Tach for Python package/module contracts and
eventually let ecosystem providers own architecture adapters where useful:

- TypeScript/JavaScript might use dependency-cruiser, Madge, ESLint boundary
  rules, or explicit configured commands.
- Go might use `go list`, `go vet`, or configured package-boundary checks.
- Other ecosystems should start with advisory configured commands before any
  blocking architecture gate.

Generic file baselines should therefore not depend on Tach.

## Proposed Config Shape

Proposed and non-binding:

```toml
[tool.agent_maintainer.file_baselines]
enabled = true
mode = "advisory"

[[tool.agent_maintainer.file_baselines.groups]]
name = "typescript-source"
include = ["src/**/*.{ts,tsx,js,jsx}"]
exclude = ["**/*.test.*", "**/*.spec.*", "**/__generated__/**"]
role = "source"
max_physical_lines = 500
max_nonblank_lines = 375
changed_file_warn = 8
changed_line_warn = 400

[[tool.agent_maintainer.file_baselines.groups]]
name = "docs"
include = ["docs/**/*.md", "*.md"]
role = "docs"
max_physical_lines = 700
max_nonblank_lines = 600
changed_file_warn = 10
changed_line_warn = 600
```

Key rules:

- Defaults must remain conservative and advisory for non-Python file groups.
- Python's existing blocking gates must not change as a side effect.
- Config should support explicit glob groups before autodetection.
- Providers may contribute suggested groups, but users should be able to
  override or disable them.
- Generated and ignored paths must be handled before line counting.
- Baselines should report exact file paths and counts, not large transcripts.

## What Can Be Generic First

These can be implemented provider-neutrally with path rules:

- file discovery by include/exclude globs;
- physical line counts;
- nonblank line counts;
- changed file and changed line counts;
- largest-file summaries;
- generated/ignored path exclusions;
- advisory JSON and Markdown summaries;
- ratcheted baselines for existing over-limit files.

These should stay provider-owned:

- source vs test classification when naming conventions vary;
- broad vs narrow suppression semantics;
- import/module architecture boundaries;
- coverage and diff coverage;
- mutation testing;
- dependency/security tool defaults;
- exact repair-fact parsing.

## Implementation Sequence

1. Add characterization tests around current Python file-length and change
   budget behavior.
2. Add a neutral file group model and parser, disabled by default.
3. Add an advisory `assess file-baselines` command that reads explicit groups
   and emits compact text/JSON.
4. Add optional non-blocking verifier check for configured file baselines.
5. Dogfood with docs and TypeScript/TSX groups in advisory mode only.
6. Add ratcheting support for known existing violations.
7. Consider opt-in blocking mode only after fixture and repo evidence proves
   low noise.

Initial implementation should stop after step 3 unless tests show the model is
too weak. That gives repositories a read-only assessment surface before any
verifier gate or ratchet can create noise.

## Acceptance Criteria

- Current Python blocking file-length/change-budget behavior remains unchanged.
- Generic file baseline checks work for any explicit glob group.
- Non-Python file groups are advisory by default.
- Output includes group, path, physical lines, nonblank lines, changed lines,
  and the next smallest useful command.
- No raw file contents are printed.
- Tests cover `.tsx`, `.md`, `.toml`, `.yaml`, and generated/ignored paths.
- Tach remains documented as Python module architecture enforcement, not the
  language-neutral baseline mechanism.
