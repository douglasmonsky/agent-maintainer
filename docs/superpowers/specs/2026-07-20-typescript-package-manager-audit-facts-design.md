# TypeScript Package-Manager Audit Facts Design

**Date:** 2026-07-20

**Phase:** Next TypeScript parity slice

**Status:** Approved for implementation planning

## Context

The TypeScript/React parity roadmap has completed package/workspace discovery,
Knip facts, OSV dependency facts, dependency-cruiser boundary facts, and
advisory LCOV changed-line coverage. Package-manager audit facts are the next
missing parity capability. The current TypeScript provider can run explicit
repository-owned commands, but it does not yet normalize audit output from
npm, pnpm, Yarn, or Bun into repairable findings.

Each package manager has a different report shape and some versions emit
newline-delimited JSON rather than one JSON document. The provider must make
those differences visible without guessing which manager a repository uses,
changing a command, or treating an advisory report as a blocking security
gate. The existing explicit-command boundary and experimental support policy
remain authoritative.

## Decision

Add one shared normalized package-manager audit fact boundary with four narrow
input adapters: npm, pnpm, Yarn, and Bun. The adapters receive bounded output
from the existing configured-command runner and return the same typed result
model. Exact repair facts and compact failed-check summaries consume that
shared model so parsing, safety, sorting, and bounds cannot drift.

The command runner continues to own execution, environment, timeout, output
capture, process status, and workspace selection. The adapters never execute a
subprocess, inspect a lockfile, search the filesystem, access the network,
install a package manager, mutate a lockfile, or apply a fix.

The package-manager name is explicit configuration. It is never inferred from
the first command token, a lockfile, packageManager, Corepack metadata, or the
report itself.

## Approaches Considered

### Shared normalized model with manager adapters — selected

Four small adapters isolate upstream schema differences while one immutable
finding model keeps repair facts and summaries consistent. Adding a manager or
supporting a report revision remains local to an adapter and its fixtures.

### Provider-specific findings and renderers — rejected

Separate npm, pnpm, Yarn, and Bun fact shapes would duplicate bounds, path
safety, deduplication, and rendering rules. Agents would receive different
repair vocabulary for equivalent vulnerabilities, and future schema changes
would create cross-manager drift.

### Reuse the OSV fact model — rejected

OSV facts describe scanner advisories and lockfile provenance. Package-manager
audit reports additionally expose directness, dependency scope, workspace
ownership, vulnerable ranges, and manager-specific fix metadata. Combining the
contracts would either discard useful audit context or make OSV parsing
manager-aware without a stable upstream reason.

## Goals

- Add explicit root and workspace package-manager audit command surfaces.
- Support npm, pnpm, Yarn, and Bun through named adapters.
- Normalize package, severity, advisory IDs, vulnerable ranges, fixed versions,
  scope, directness, workspace, safe path, manager, and report outcome.
- Reuse one normalized model for exact repair facts and compact summaries.
- Handle one JSON document and bounded NDJSON where a manager emits records per
  line.
- Keep malformed neighbors from hiding valid findings while failing closed when
  the complete input is invalid.
- Deduplicate equivalent findings and sort before applying every retention
  limit.
- Preserve explicit command exit status and keep findings advisory.
- Add synthetic contract fixtures plus pinned public npm and pnpm projections;
  add Yarn and Bun projections when stable public captures are available.
- Document configuration, evidence, limitations, provider status, roadmap
  order, and DocSync ownership.

## Non-Goals

- No automatic package-manager or command detection.
- No command construction, reporter-flag injection, shell evaluation, or
  package-manager installation.
- No lockfile discovery, lockfile rewriting, dependency updates, or autofix.
- No vulnerability thresholds, advisory allowlists, baselines, or blocking
  promotion of the TypeScript provider.
- No resolution of dependency paths beyond fields explicitly supplied by the
  report.
- No interpretation of package-manager policy files, workspace manifests, or
  lifecycle scripts.
- No attempt to make npm, pnpm, Yarn, and Bun reports interchangeable outside
  the normalized fact fields.
- No change to the existing command runner's timeout, environment, or exit
  status semantics.

## Configuration And Check Ownership

The top-level configuration adds an explicit manager alongside an exact command
array and the provider's existing profile pattern:

~~~toml
[tool.agent_maintainer]
enable_typescript = true
typescript_package_manager_audit_manager = "npm"
typescript_package_manager_audit_command = ["npm", "audit", "--json"]
typescript_package_manager_audit_profiles = ["full", "ci"]
~~~

The command and manager are both required for an enabled audit check. The
manager value is one of npm, pnpm, yarn, or bun; an empty command keeps the
optional check skipped, matching the existing TypeScript command pattern. The
command is passed unchanged to the normal runner. Examples for pnpm, Yarn, and
Bun are documented as repository-owned command choices rather than defaults.

Workspaces may own their own explicit manager and command:

~~~toml
[tool.agent_maintainer.workspaces.web]
typescript_package_manager_audit_manager = "pnpm"
typescript_package_manager_audit_command = ["pnpm", "audit", "--json"]
~~~

Workspace checks use the root profile selection, as Knip and
dependency-cruiser do. Stable check names are:

- typescript-package-manager-audit
- typescript-package-manager-audit:<workspace>

The workspace label is orchestration metadata. It is not read from a report
and is not guessed from a package path. A configured manager with no command,
or a command with no valid manager, produces the existing optional
configuration diagnostic and no subprocess invocation.

## Adapter Input Boundary

The orchestrator passes each adapter a bounded UTF-8 report and the explicit
manager, workspace label, source label, and command outcome. It may pass
stdout or an explicitly declared artifact through existing bounded artifact
plumbing; the adapter never discovers another file.

Each adapter accepts the manager's documented JSON projection without requiring
the provider to append a reporter flag:

- **npm:** the current vulnerabilities map is normative; the legacy
  advisories map may be accepted for compatibility when its entries carry an
  explicit advisory ID. Package records may contribute severity, vulnerable
  range, directness, scope, advisory references, and fix metadata.
- **pnpm:** advisory records and their metadata are normalized from the
  manager's JSON report. Both object reports and supported line-delimited
  advisory records are accepted when their package and advisory identifiers
  are explicit.
- **Yarn:** auditAdvisory records in NDJSON are normative for the initial
  adapter; summary and action records contribute only bounded report metadata.
  The adapter also accepts a documented object projection when supplied by a
  repository-owned wrapper.
- **Bun:** the documented JSON object or NDJSON advisory projection is
  accepted. The adapter recognizes only fields with an explicit package,
  severity, and advisory identifier and ignores unrelated command chatter.

The implementation records the exact supported projection for each adapter in
fixtures and documentation. It does not claim that every release's human
output or undocumented field is supported.

### JSON and NDJSON validation

For a JSON report, the root must be an object or an explicitly supported array
of advisory records. For NDJSON, blank lines are ignored and each non-empty
line is decoded independently. A malformed neighbor does not discard valid
records from the same report. If no line or root can be decoded into a
supported report container, the result is invalid input and falls back to the
bounded raw log.

Unsupported optional fields are ignored locally. A record without an explicit
package or advisory identifier is not a finding; it cannot be repaired by
constructing an ID from a package name, range, URL, or line number.

## Normalized Result And Finding Contract

The shared parser returns a result with:

- manager: one of npm, pnpm, yarn, or bun;
- workspace: the configured root/workspace label, if any;
- outcome: clean, findings, or invalid-input;
- findings: the bounded, sorted normalized findings;
- supported_count, retained_count, and omitted_count metadata.

Each finding contains:

- package name;
- normalized severity (critical, high, moderate, low, info, or unknown),
  preserving an unknown upstream label only as bounded display metadata;
- sorted advisory IDs;
- sorted vulnerable ranges;
- sorted fixed versions;
- optional explicit scope and directness;
- optional safe report path or source label;
- manager and workspace ownership;
- bounded advisory title/summary when the report supplies one.

Scope and directness are presence-based facts. The parser records an explicit
dev, prod, optional, or peer scope and explicit direct/indirect values when
supplied; it never infers them from dependency paths, package manifests,
lockfiles, or the presence of a fix.

Advisory IDs are deduplicated and sorted. Equivalent records from one report
are merged only when their explicit manager, workspace, package, advisory IDs,
range, and fixed-version facts agree. A package may retain multiple advisory
IDs when the upstream report explicitly associates them with one finding.

The exact repair fact uses the stable check name, a safe relative path when
available, the first sorted advisory ID as symbol, normalized severity, and a
bounded message containing package, advisory IDs, ranges, fixes, scope,
directness, manager, workspace, and source label. Empty clauses are omitted.
The compact summary uses the same finding object and message ordering.

## Path Safety

Report paths are display and provenance data, not filesystem instructions. A
path can become a context target only when it is a normalized repository-
relative path with no root, drive prefix, dot identity, or parent traversal.
Absolute POSIX paths, Windows drive/UNC paths, empty values, overlong values,
and traversal are never emitted as fact targets. An unsafe value may retain a
validated basename as a display label; otherwise the label is <unknown source>.
The adapter never consults the current working directory or guesses a
repository root.

## Bounds And Determinism

The parser applies bounds after normalization and deterministic sorting:

- at most 500 findings per report;
- at most 25 advisory IDs, vulnerable ranges, and fixed versions per finding;
- at most 200 characters for every normalized scalar;
- at most 50 rendered compact-summary lines, with one truthful omission line;
- at most 1,000 characters for one exact fact or summary message;
- at most five exact facts per failed check through the existing context pack.

Sorting uses manager, workspace, safe source label, package, severity rank,
advisory IDs, vulnerable ranges, and fixed versions. Input order, NDJSON line
order, and map insertion order therefore cannot change retained facts.

## Outcome And Exit Semantics

The parser's result boundary has explicit exit-style semantics:

- 0 / clean: valid report with no normalized findings;
- 1 / findings: valid report with one or more findings; findings remain
  advisory;
- 2 / invalid-input: invalid JSON, unsupported root, or no supported records
  in an otherwise malformed report.

These parser outcomes are not a substitute for the configured command's
process status. The runner preserves the exact subprocess exit code and
output. Parsing cannot turn a command failure into success, suppress a
command failure, or create a blocking gate. A valid audit report with findings
therefore remains advisory even if the manager exits nonzero, and a clean
report remains subject to the command's own status.

## Data Flow And Ownership

~~~text
explicit root/workspace manager + command
  -> existing TypeScript command runner
     -> bounded JSON or NDJSON output
        -> manager adapter
           -> shared normalized result (sorted, safe, max 500)
              -> compact advisory summary (max 50 lines)
              -> exact repair facts (existing max 5 per check)
~~~

The parser belongs in the inward agent_repair_facts domain, with a small
manager-adapter module and shared audit models. TypeScript provider
configuration and orchestration remain in agent_maintainer; they depend on the
parser, never the reverse. Any new domain module receives an explicit Tach
ownership edge in the same implementation change. No architecture policy is
relaxed for this slice.

## Testing And Evidence

Implementation is test-first and must cover:

- root and workspace configuration, manager validation, profile selection,
  stable check names, and exact command preservation;
- current npm and pnpm object projections, Yarn NDJSON, and Bun object/NDJSON;
- duplicate advisory IDs, multiple ranges/fixes, explicit scope/directness,
  root versus workspace ownership, and severity normalization;
- malformed JSON, malformed NDJSON neighbors, unsupported roots, empty reports,
  missing package/ID fields, control characters, and unsupported severities;
- absolute, drive-qualified, UNC, traversal, dot, empty, unsafe-basename, and
  overlong paths;
- deterministic sorting and all finding, list, scalar, message, summary-line,
  and context-pack bounds;
- parser outcomes clean, findings, and invalid-input without changing
  subprocess exit status;
- offline replay of at least two pinned public projections: the existing npm
  jsynowiec/node-typescript-boilerplate revision
  550dfd2a976d69254ed71eb6f5a6c5ee20060807 and pnpm
  vitest-dev/eslint-plugin-vitest revision
  7c697f8a53d7d7551b00ef11217d58cd45a0cf7d;
- Yarn and Bun public captures when stable, reproducible reports are available;
  otherwise synthetic fixtures remain the normative contract and the missing
  external capture is documented.

External captures record only public repository URL, pinned revision, UTC
collection time, manager/tool/runtime versions, exact command, exit status,
report hash and byte count, supported/retained counts, and bounded normalized
findings. No clone, dependency tree, local absolute path, credential, or full
report is committed. Tests replay projections offline and require no network,
package installation, or package-manager binary.

## Documentation And Roadmap

The implementation phase updates:

- docs/typescript-javascript-provider.md with explicit manager/command
  examples, normalized fields, safety and bounds, advisory status, and the
  supported projection matrix;
- docs/configuration-reference.md with manager, command, profile, workspace,
  defaults, and validation behavior;
- provider-status, supported-scan/tool guidance, and setup-advisor prose so no
  document implies automatic manager selection or blocking security review;
- the TypeScript parity roadmap and a focused phase record, marking this slice
  complete only after implementation and evidence gates pass;
- .docsync/trace.yml and its focused tests when public claims or configuration
  ownership change. Generated DocSync output remains uncommitted.

The next TypeScript slices remain generated-file/framework policy and a
blocking-promotion assessment. Mutation, Nx boundaries, React hooks/a11y
recommendations, and Stryker remain later work. TypeScript/JavaScript stays
experimental throughout this slice.

## Acceptance Criteria

- Root and workspace audit checks run only the explicitly configured manager
  and command arrays.
- npm, pnpm, Yarn, and Bun adapters return one normalized contract with no
  manager inference or command mutation.
- Valid findings produce deterministic compact summaries and exact repair facts
  through one shared parser.
- Malformed reports fail closed to bounded raw output; malformed neighbors do
  not hide valid findings.
- All path, scalar, list, finding, message, summary, and context bounds have
  adversarial tests.
- Parser outcome 1 is advisory and never promotes the provider to blocking;
  configured subprocess exit status remains authoritative.
- Two pinned public npm/pnpm projections replay offline without private data;
  Yarn/Bun evidence is either pinned or explicitly documented as fixture-only.
- Tach ownership, configuration reference, provider docs, roadmap, and DocSync
  claims agree.
- Focused tests, static typing/lint, architecture, documentation, full local
  verification, and independent review pass before the implementation phase is
  marked complete.

## Recorded Decisions

The user approved the recommended self-approval workflow choices:

1. A shared normalized audit model with four narrow manager adapters.
2. Explicit manager plus exact root/workspace command arrays; no inference.
3. Advisory-only findings with parser outcomes equivalent to 0/1/2 and
   unchanged subprocess exit status.
4. Bounded, path-safe, deterministic output shared by exact facts and compact
   summaries.
5. Synthetic fixtures for all managers, pinned npm/pnpm projections, and
   Yarn/Bun projections when stable public captures are available.

## Primary References

- npm audit: <https://docs.npmjs.com/cli/commands/npm-audit>
- pnpm audit: <https://pnpm.io/cli/audit>
- Yarn audit: <https://yarnpkg.com/cli/npm/audit>
- Bun audit: <https://bun.sh/docs/pm/cli/audit>
- TypeScript/JavaScript provider: docs/typescript-javascript-provider.md
- TypeScript/React parity roadmap: docs/roadmap/typescript-react-parity-roadmap.md
