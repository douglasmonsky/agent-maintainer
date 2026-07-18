# TypeScript Dependency-Cruiser Facts Design

**Date:** 2026-07-17
**Status:** Approved through the recorded recommended-choice workflow
**Phase:** 181

## Context

Agent Maintainer's experimental TypeScript/JavaScript provider already runs
explicit lint, typecheck, test, and Knip commands and can extract bounded repair
facts from their stable outputs. Phase 180 added ecosystem-neutral OSV facts.
The parity roadmap names package-manager audit facts next and then
dependency-cruiser architecture-boundary facts.

The user has intentionally advanced the architecture slice first. Phase 181
therefore implements dependency-cruiser facts now. Package-manager audit facts
remain the next TypeScript parity slice after this phase. This sequencing change
does not promote the provider or make architecture checks blocking by default.

Tach remains the Python architecture backend. Dependency-cruiser is the closest
TypeScript/JavaScript equivalent because it combines explicit boundary rules
with a documented machine-readable cruise-result schema. It does not replace
Tach, Archguard, or Agent Maintainer's own Python package contracts.

## Decision

Add one explicit TypeScript dependency-cruiser command surface and a dedicated
parser for dependency-cruiser's JSON `summary.violations` contract. Root and
workspace commands use the existing provider-owned configured-command runner.
The runner preserves the exact command and process exit status; Agent Maintainer
does not append reporter flags, infer a package manager, install the tool, or
invent boundary rules.

The parser emits deterministic, path-safe, bounded repair facts and compact
summaries for valid rule violations. Malformed or unsupported JSON produces no
structured facts and leaves the normal bounded raw log authoritative.

## Approaches Considered

### Dedicated dependency-cruiser check and parser — selected

This preserves a specific architecture contract, stable check name, explicit
configuration, and a parser aligned with the upstream JSON schema. It leaves a
clear future seam for declared Nx boundaries without pretending the two tools
share one report format.

### Parse boundary rules from TypeScript lint output — rejected

`eslint-plugin-boundaries` can report violations through ESLint JSON, but those
violations are generic lint messages rather than a dedicated architecture
graph/result contract. Reusing `typescript-lint` would also obscure check
ownership, profiles, documentation, and future architecture-specific evidence.

### Use Madge graph and cycle output — rejected

Madge is useful for dependency graphs and cycles but is not a general boundary
rule engine. Treating it as Tach parity would overstate its enforcement model.

## Goals

- Register explicit root and workspace dependency-cruiser commands.
- Default the new check to the `full` and `ci` profiles.
- Parse dependency-cruiser JSON summary violations into exact repair facts.
- Reuse the parser for compact failed-check summaries and context facts.
- Preserve rule name, upstream severity, violation type, source, and target.
- Reject unsafe source paths as context targets and sanitize displayed paths.
- Bound parser retention, summary rendering, context use, scalars, and messages.
- Record deterministic offline compatibility evidence from two pinned public
  TypeScript repositories with different package-manager/shape evidence.
- Keep TypeScript/JavaScript experimental and the check opt-in.

## Non-Goals

- No inferred `depcruise`, npm, pnpm, Yarn, Bun, or Corepack command.
- No automatic `--output-type json` or `-T json` mutation.
- No dependency-cruiser installation, configuration generation, or rule
  synthesis in normal execution.
- No thresholds, baseline lifecycle, autofix, or process exit-code override.
- No Nx, ESLint-boundaries, or Madge adapter in Phase 181.
- No blocking TypeScript architecture promotion.
- No change to Tach or Archguard's Python ownership.
- No generic third-party architecture-report framework.

## Configuration And Check Ownership

The top-level configuration adds:

```toml
[tool.agent_maintainer]
enable_typescript = true
typescript_dependency_cruiser_command = [
  "pnpm",
  "exec",
  "depcruise",
  "--output-type",
  "json",
  "src",
]
typescript_dependency_cruiser_profiles = ["full", "ci"]
```

The exact long reporter option is used in documentation for readability. The
upstream `-T json` spelling is equally valid because Agent Maintainer never
inspects or rewrites the command.

Workspaces may own exact commands:

```toml
[tool.agent_maintainer.workspaces.web]
typescript_dependency_cruiser_command = [
  "pnpm",
  "--filter",
  "web",
  "exec",
  "depcruise",
  "--output-type",
  "json",
  "src",
]
```

Stable check names are:

- `typescript-dependency-cruiser`
- `typescript-dependency-cruiser:<workspace>`

Workspace checks use the root profile selection, matching the existing Knip
model. When TypeScript is enabled and the root command is empty, the root check
uses the normal optional empty-command skip. Workspace checks exist only for
workspaces that configure a command.

## JSON Input Contract

The supported input is dependency-cruiser's documented cruise-result object:

```json
{
  "modules": [],
  "summary": {
    "violations": [
      {
        "from": "src/ui/view.ts",
        "to": "src/data/private.ts",
        "type": "dependency",
        "rule": {
          "name": "ui-not-to-data",
          "severity": "error"
        }
      }
    ]
  }
}
```

Only `summary.violations` is authoritative for this phase. The parser does not
walk the full `modules`, `folders`, `cycle`, `via`, metrics, environment,
configuration, or rule-set graphs. That keeps work proportional to actionable
violations and avoids duplicating data present at multiple schema levels.

A supported violation requires:

- a non-empty string `from` plus a usable non-empty `to` or `unresolvedTo`;
- an object `rule` with non-empty string `name`;
- rule severity `error`, `warn`, or `info`;
- optional violation type from dependency-cruiser's documented set:
  `dependency`, `module`, `reachability`, `cycle`, `instability`, or `folder`.

Unknown severities, `ignore` violations, malformed neighbors, and unsupported
violation types are skipped independently. `unresolvedTo` supplies the display
target only when `to` is empty or unusable; it never becomes a context path.
The root must contain object `summary` and array `violations` to be considered a
valid structured result.

## Normalized Finding And Fact Contract

One normalized finding contains:

- source context path or `None`;
- safe source display label;
- safe target display label;
- rule name;
- upstream severity;
- optional supported violation type.

The exact fact uses the full root or workspace-suffixed check name. Its `path`
is the source only when that source is a safe repository-relative path. Its
`symbol` is the rule name. Its message renders a bounded form such as:

```text
src/ui/view.ts -> src/data/private.ts: ui-not-to-data [error; dependency]
```

Fact severity preserves dependency-cruiser's `error`, `warn`, or `info` value.
The target remains display-only in this phase so context selection cannot treat
external modules or unsafe paths as repository files.

## Bounds, Safety, And Determinism

- Decode JSON once and examine only `summary.violations`.
- Normalize control characters to whitespace before rendering.
- Cap normalized scalar values at 200 characters.
- Treat paths longer than 500 characters as non-targetable.
- Reject absolute POSIX paths, absolute or drive-qualified Windows paths,
  parent traversal, empty paths, and `.` as context targets.
- Reduce unsafe source or target values to a safe basename when possible,
  otherwise use `<unknown source>` or `<unknown target>`.
- Sort findings by source label, target label, rule name, severity, and type.
- Retain at most 500 findings after sorting.
- Cap one rendered fact message at 1,000 characters.
- Render at most 50 total compact-summary lines, reserving the last line for an
  omission marker when findings exceed the visible bound.
- Keep the existing five facts per failed check in context packs.

Parser metadata retains the supported count before the 500-finding slice so the
summary omission marker remains truthful. It does not retain raw ignored fields
or local checkout roots.

## Data Flow

1. Configuration loads an exact root or workspace command array.
2. The TypeScript provider registers the selected check and profiles.
3. The normal runner executes the exact array and preserves exit status/output.
4. The structured TypeScript summarizer recognizes the check family and calls
   the dedicated parser.
5. The repair-fact registry calls the same parser for exact context facts.
6. Malformed or unsupported output yields no structured summary or facts, so
   existing bounded raw-log behavior remains authoritative.

The parser lives in `agent_repair_facts`; orchestration and rendering live in
`agent_maintainer`. Tach domain declarations must preserve that dependency
direction. Any architecture-policy edit receives a matching decision note.

## Exit And Error Semantics

- Exit `0` remains pass even if the JSON contains warning or informational
  notices; valid findings are retained as a non-blocking warning summary.
- Any nonzero exit remains failure through the existing check runner.
- Parser success or failure never upgrades, suppresses, or replaces the process
  result.
- Root and workspace cruise-result output uses a five-million-character
  capture limit instead of the generic one-million-character command limit.
- Empty violations produce no structured summary or repair facts.
- Malformed JSON, recursion errors, invalid root shapes, and malformed neighbors
  fail closed to bounded raw output without raising into verification.

## External Repository Evidence

Phase 181 records two pinned public TypeScript repositories, selected after the
implementation parser exists:

- one npm/package-lock repository;
- one pnpm workspace repository.

The capture runs a pinned dependency-cruiser release with JSON output in a
task-specific temporary directory. It never runs arbitrary package scripts.
When dependencies are required for resolution, installation must use the
repository's lockfile with lifecycle scripts disabled. Committed projections
retain only public repository metadata, pinned commit, UTC collection time,
tool and Node versions, exact command, exit status, configuration and lockfile
hashes, raw-report hash and byte count, supported/retained counts, and at most
25 normalized violations.

Raw clones, dependency trees, full cruise graphs, local absolute paths, and
temporary files are not committed. Normal tests replay projections offline and
require neither network access nor a dependency-cruiser binary.

## Testing

Test-driven implementation covers:

- top-level and workspace configuration loading;
- default `full`/`ci` profiles and empty-command behavior;
- exact root/workspace command preservation and check names;
- supported violation types and severity preservation;
- malformed root, summary, violation, rule, and neighbor handling;
- ignored/unknown severities and unsupported types;
- deterministic sorting and 500-finding retention;
- safe relative sources plus absolute, traversal, drive, control-character,
  overlong, dot, and empty path rejection;
- 200-character scalar and 1,000-character message bounds;
- 50-line compact summaries and truthful omission counts;
- five-fact context retention for the new check family;
- offline replay of two bounded public compatibility projections;
- documentation, configuration reference, DocSync, and roadmap claims.

Focused tests run after every red/green cycle. The coherent phase then runs
Ruff, Wemake/flake8, Pyright, Tach exact, Archguard decision checks, DocSync,
Markdownlint, the repository's full profile, and an independent batched review.

## Documentation And Roadmap

Public docs will:

- show explicit root and workspace commands with JSON output;
- explain that dependency-cruiser is the TypeScript Tach-like boundary tool,
  not a replacement for Python Tach or Archguard;
- state that Agent Maintainer never installs the tool or invents rules;
- document the output, path-safety, and retention contracts;
- keep TypeScript/JavaScript experimental and advisory;
- mark Phase 181 complete only after all acceptance evidence passes;
- record package-manager audit facts as the next parity slice;
- keep declared Nx boundary support as a later independent phase.

Because Phase 181 is based on the open Phase 180 branch, its draft pull request
targets `codex/typescript-osv-facts`. After PR #399 merges, the Phase 181 branch
can be updated or retargeted to `main` without rewriting history.

## Acceptance Criteria

- The new root and workspace checks run only explicit configured arrays.
- Default profiles are `full` and `ci`; no blocking default is added.
- Valid cruise-result summary violations produce deterministic exact facts and
  compact summaries through one shared parser.
- All parser and rendering bounds have adversarial tests.
- Unsafe source paths never become context targets or committed fixture paths.
- Parser behavior never changes the configured command's exit result.
- Two pinned public projections replay offline and contain no local paths or
  private data.
- Tach ownership remains exact and any policy change has an ADR.
- Public docs, configuration reference, roadmap, and DocSync evidence agree.
- Focused, static, architecture, documentation, full-profile, and hosted CI
  gates pass before merge.
- TypeScript/JavaScript remains experimental.

## Primary References

- Dependency-cruiser CLI:
  <https://github.com/sverweij/dependency-cruiser/blob/main/doc/cli.md>
- Dependency-cruiser cruise-result schema:
  <https://github.com/sverweij/dependency-cruiser/blob/main/src/schema/cruise-result.schema.json>
- Dependency-cruiser JSON reporter:
  <https://github.com/sverweij/dependency-cruiser/blob/main/src/report/json.mjs>
- Dependency-cruiser real-world samples:
  <https://github.com/sverweij/dependency-cruiser/blob/main/doc/real-world-samples.md>
- ESLint formatters:
  <https://eslint.org/docs/latest/use/formatters/>
- Madge:
  <https://github.com/pahen/madge>
