# TypeScript Knip Facts Design

Date: 2026-07-17

Status: approved for implementation planning pending written-spec review

## Context

Phase 178 completed advisory package-manager and workspace evidence. The next
TypeScript/React parity slice is Knip unused-code and dependency facts, the
closest ecosystem replacement for the Python provider's Vulture and Deptry
surfaces.

Agent Maintainer already has an experimental TypeScript provider with explicit
root and workspace-owned commands, compact structured summaries, and exact
repair facts for ESLint, TypeScript, Jest, Vitest, Istanbul, and LCOV output.
Knip should extend those seams without inferring a package manager, script,
workspace owner, or executable command.

Knip's JSON reporter is invoked with `knip --reporter json`. The current
contract is source-defined rather than published as an independently versioned
schema. Knip documents exit code `0` for no issues, `1` for lint findings, and
`2` for bad input or an internal failure.

## Decision

Phase 179 adds a dedicated, opt-in `typescript-knip` check with a dedicated
Knip JSON parser. The provider executes only configured command arrays and
preserves Knip's exit status. Agent Maintainer adds no threshold, command
suffix, package-manager choice, or automatic enablement.

The parser recognizes the bounded unused-code and dependency categories in
Knip JSON, produces deterministic compact summaries, and emits exact repair
facts. Unknown future fields are ignored. Malformed records are isolated so
valid sibling findings remain useful.

TypeScript/JavaScript remains experimental after Phase 179.

## Goals

- Add an explicit root Knip command and explicit workspace-owned Knip commands.
- Preserve normal Knip exit semantics for configured checks.
- Parse stable unused-file, export, type, dependency, binary, and unresolved
  facts from JSON reporter output.
- Provide compact failed-check summaries and exact context-pack repair facts.
- Support root and workspace-suffixed check names consistently.
- Record reproducible comparison evidence from two public TypeScript
  repositories at pinned commits.
- Keep parsing bounded, deterministic, tolerant of additive schema changes,
  and independent from a local Knip dependency.

## Non-Goals

- No inferred `knip`, npm, pnpm, Yarn, Bun, or Corepack command.
- No command synthesis from Phase 178 repository evidence or package scripts.
- No automatic `--reporter json` mutation; the configured command remains
  exact and documentation shows the required reporter option.
- No Agent Maintainer issue threshold or reinterpretation of Knip's exit code.
- No default TypeScript enablement, blocking-gate promotion, or maturity change.
- No generic third-party JSON adapter framework.
- No cycles, duplicate-export groups, catalog entries, enum members,
  namespace members, or class-member policy in this slice.
- No live-network dependency in the committed test suite.

## Configuration And Check Ownership

Root configuration adds:

```toml
[tool.agent_maintainer]
enable_typescript = true
typescript_knip_command = ["pnpm", "exec", "knip", "--reporter", "json"]
```

`typescript_knip_profiles` defaults to `full` and `ci`. Knip is omitted from
`precommit` by default because repository-wide analysis can be materially more
expensive than linting changed work.

Workspace configuration adds:

```toml
[tool.agent_maintainer.workspaces.web]
typescript_knip_command = [
  "pnpm",
  "--filter",
  "web",
  "exec",
  "knip",
  "--reporter",
  "json",
]
```

Stable check names are:

- `typescript-knip`
- `typescript-knip:<workspace>`

Workspace checks use the root `typescript_knip_profiles` selection, matching
the existing lint, typecheck, and test command model. An enabled TypeScript
provider with no root Knip command reports the normal explicit empty-command
skip. Workspace checks exist only for workspaces with a configured Knip
command.

The provider never appends reporter flags or changes the command. A repository
that wants structured facts must configure `--reporter json`; other output is
retained as raw check output.

## JSON Input Contract

The parser accepts a JSON object with an `issues` array and an optional
top-level `files` array of unused-file paths. Each issue group must have a
string `file` and may contain arrays for recognized categories. Current Knip
records may include `name`, `namespace`, `kind`, `specifier`, `line`, `col`,
and `pos`; only validated fields are consumed. Absolute paths and paths with
parent traversal are rejected so facts remain repository-relative.

Phase 179 recognizes:

| Knip category | Normalized fact |
|---|---|
| top-level `files` | unused file |
| `exports`, `nsExports` | unused export |
| `types`, `nsTypes` | unused type |
| `dependencies`, `devDependencies`, `optionalPeerDependencies` | unused dependency |
| `unlisted` | unlisted dependency |
| `binaries` | unused binary |
| `unresolved` | unresolved import or binary |

Each exact fact contains:

- the full root or workspace-suffixed check name;
- a repository-relative path;
- available line and column values exactly as reported by Knip;
- a stable Knip category symbol;
- the finding name or specifier and a concise category message; and
- `error` severity, consistent with a Knip finding exit.

Known category items with invalid shapes are skipped. Valid neighboring groups
and items still produce facts. Unknown top-level or group fields are ignored.
An invalid JSON root or missing/non-array `issues` field produces no structured
summary or facts; the raw log and command result remain authoritative.

## Bounds And Determinism

Valid findings are sorted by path, category, name, line, and column, then capped
at 500 normalized findings from one payload. Compact failed-check output shows
at most 50 lines and reports the omitted count. Exact context packs retain the
existing maximum of 5 facts per check.

These limits bound context and rendering work after JSON decoding. Existing
verifier log-size and exact-fact read budgets remain the outer input boundary.
No raw repository source or private record is copied into new artifacts.

## Data Flow

1. Configuration loads an exact root or workspace Knip command.
2. The TypeScript provider creates `typescript-knip` or
   `typescript-knip:<workspace>` with `full` and `ci` profiles.
3. The normal check runner executes the exact command and retains raw output,
   artifacts, exit status, and timing.
4. Compact reporting canonicalizes only the TypeScript check family for parser
   selection while preserving the full check name in output.
5. A dedicated `agent_repair_facts.parsers.typescript_knip` module validates
   and normalizes the JSON payload.
6. Compact summaries render bounded editor-oriented lines.
7. Exact-fact dispatch uses the same parser and preserves the full root or
   workspace check name in every fact.

Check-family normalization is deliberately narrow: only known TypeScript
checks split the optional `:<workspace>` suffix. This also makes existing
workspace lint, typecheck, and test facts consistent without changing their
commands or parser semantics.

## Exit And Error Semantics

- Exit `0`: the configured check passes. Empty `issues` JSON produces no repair
  facts.
- Exit `1`: the check fails normally and structured Knip findings improve the
  compact summary and repair facts.
- Exit `2`: the check fails normally. If no valid issue payload is available,
  Agent Maintainer falls back to bounded raw output.
- A user-configured `--no-exit-code` remains the repository's choice; Agent
  Maintainer neither adds nor removes it.
- Parser errors never replace, suppress, or upgrade the command exit status.

## External Repository Evidence

Phase 179 records two bounded public-repository comparisons:

1. TanStack Query at commit
   `97db5d244715642fb63d9ce78566aa632cdfdc07`, using its checked `knip.json`,
   pnpm workspace metadata, and lockfile-pinned Knip installation.
2. Astro at commit `91992ef2ccd9a90fa4270633eb4f5d3b811bf315`,
   using its checked `knip.js`, exact Knip `5.82.1` dependency, Node version,
   and pnpm lockfile.

The implementation workflow runs a Knip-only JSON command in temporary clones.
Committed fixtures retain only public source metadata, the pinned commit,
environment and reproduction command, exit code, bounded reporter output or
normalized counts, and relevant configuration/lockfile hashes. Dependency
trees, clones, caches, and unbounded logs are not committed.

Synthetic fixtures remain the authoritative category coverage because healthy
external repositories may emit an empty issue set. External comparisons prove
compatibility with real configuration and workspace shapes, not universal
Knip correctness.

## Testing

The implementation plan must include test-driven coverage for:

- root config loading, profile defaults, empty-command skip, and exact command
  preservation;
- workspace config loading and stable suffixed check names;
- all recognized Knip categories and optional location fields;
- deterministic ordering and the 500-finding normalization bound;
- invalid JSON, invalid roots, malformed groups, malformed category arrays,
  malformed items, unknown fields, and valid-neighbor preservation;
- compact summaries with the 50-line omission marker;
- exact facts for root and workspace check names;
- existing workspace lint, typecheck, and test fact dispatch after narrow
  check-family normalization;
- recorded TanStack Query and Astro comparison metadata and normalized results;
- configuration reference generation, provider catalog order, doctor/setup
  guidance, DocSync traceability, and roadmap completion wording; and
- exact Tach dependencies plus the complete focused and broad verifier suites.

## Documentation And Roadmap

The slice is Phase 179: TypeScript Knip Unused-Code And Dependency Facts.

Public documentation will:

- show root and workspace command examples with `--reporter json`;
- state that Agent Maintainer never installs Knip or infers a command;
- recommend an exact or lockfile-pinned Knip release because the reporter
  contract is release-coupled;
- describe supported and deferred issue categories;
- retain TypeScript/JavaScript experimental status; and
- mark Phase 179 complete while naming OSV and package-manager audit facts as
  the next parity slice.

DocSync claims connect the public provider and repair-fact statements to parser,
provider, configuration, and external-evidence tests.

## Alternatives Considered

### Treat Knip As TypeScript Lint Output

Rejected because it conflates ESLint rule findings with repository-wide unused
code and dependency integrity. It also makes configuration, profiles, repair
symbols, and workspace ownership ambiguous.

### Parse Only Pre-Existing Artifacts

Rejected for this phase because an explicit configured command provides the
useful end-to-end workflow the user selected. Artifact parsing can be added
later if repositories standardize a checked Knip report path.

### Build A Generic Third-Party JSON Adapter Framework

Rejected as premature. OSV and dependency-cruiser have different schemas,
execution boundaries, and artifact needs. A dedicated Knip parser is smaller,
clearer, and easier to replace if the reporter contract changes.

## Acceptance Criteria

Phase 179 is complete when:

- root and workspace Knip commands are explicit, opt-in, and profile-scoped;
- no evidence or package metadata becomes an executable command;
- recognized Knip JSON categories produce deterministic bounded summaries and
  exact facts;
- malformed and additive schema cases follow the documented fail-closed rules;
- Knip exit status remains authoritative;
- the TanStack Query and Astro comparison fixtures are reproducible and public;
- TypeScript remains experimental with no default blocking promotion;
- focused tests, strict typing, architecture checks, DocSync, full local
  verification, and hosted CI pass; and
- the phase is documented, reviewed, merged independently to `main`, and the
  next roadmap slice remains OSV/package-manager audit facts.

## Primary References

- Knip CLI: <https://knip.dev/reference/cli>
- Knip reporters: <https://knip.dev/features/reporters>
- Knip issue types: <https://knip.dev/reference/issue-types>
- Knip JSON reporter source:
  <https://github.com/webpro-nl/knip/blob/main/packages/knip/src/reporters/json.ts>
- TanStack Query comparison:
  <https://github.com/TanStack/query/tree/97db5d244715642fb63d9ce78566aa632cdfdc07>
- Astro comparison:
  <https://github.com/withastro/astro/tree/91992ef2ccd9a90fa4270633eb4f5d3b811bf315>
