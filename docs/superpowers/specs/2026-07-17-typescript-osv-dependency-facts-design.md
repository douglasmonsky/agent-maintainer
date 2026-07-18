# TypeScript OSV Dependency Facts Design

**Date:** 2026-07-17  
**Phase:** 180  
**Status:** Approved for implementation planning

## Context

The TypeScript/React parity roadmap names lockfile-aware OSV dependency
scanning as the next slice after Phase 179 Knip facts. Agent Maintainer already
has an ecosystem-neutral, optional `osv-scanner` check, configuration fields,
tool guidance, and a compact artifact summary. It does not emit exact repair
facts for OSV findings, and its summary reads package versions from the legacy
outer package entry rather than OSV Scanner v2's nested `package.version`.

Phase 180 should close that repair-context gap without creating a duplicate
TypeScript scanner command. OSV Scanner remains useful for mixed-language
repositories, while the evidence for this phase concentrates on npm and pnpm
lockfiles because TypeScript/JavaScript is the active parity track.

## Decision

Reuse the existing global `osv-scanner` check and add one shared OSV Scanner v2
parser under `agent_repair_facts`. Exact repair facts and compact verifier
summaries will consume the same normalized findings so schema handling,
deduplication, path safety, ordering, and bounds cannot drift.

The parser will emit one finding per OSV alias group. It will retain package,
ecosystem, installed version, canonical advisory ID, aliases, fixed versions,
group severity, bounded advisory summary, source type, and safe lockfile
provenance. It will support the current nested package version and the existing
legacy outer-version shape for compatibility.

Phase 180 does not add a TypeScript-specific OSV command, enable the scanner by
default, change profile defaults, or add package-manager audit execution.

## Goals

- Add exact `osv-scanner` artifact repair facts.
- Parse the current OSV Scanner v2 machine JSON contract.
- Deduplicate alias-equivalent CVE, GHSA, OSV, and ecosystem advisory records.
- Preserve actionable package, fix-version, and lockfile provenance.
- Reject or redact unsafe source paths before they enter summaries or context.
- Make compact summaries use the same normalized parser as exact facts.
- Keep deterministic ordering and bounded output.
- Add npm and pnpm compatibility evidence from pinned public repositories.
- Keep TypeScript/JavaScript experimental and OSV optional/manual by default.

## Non-Goals

- A new `typescript_osv_command` or workspace OSV command surface.
- npm, pnpm, Yarn, or Bun audit command execution or output parsing.
- Automatic package-manager selection, command inference, installation, or
  dependency updates.
- Automatic vulnerability ignores, config edits, remediation, or lockfile
  mutation.
- Vulnerability thresholds, advisory allowlists, or blocking TypeScript
  promotion.
- Expanding OSV execution beyond the existing configured arguments and
  profiles.
- Full Yarn, Bun, npm-shrinkwrap, or workspace evidence in this slice.
- Changing the scanner's process exit status or network behavior.

## Existing Check Boundary

The existing global fields remain authoritative:

```toml
[tool.agent_maintainer]
enable_osv_scanner = true
osv_scanner_args = ["scan", "source", "-r", "."]
osv_scanner_profiles = ["manual"]
```

The catalog continues to append `--format json --output-file
<diagnostic-artifacts-dir>/osv-scanner.json`. The command runs only in selected
profiles, requires the configured external executable when enabled, and keeps
the scanner's exit code. Phase 180 changes artifact interpretation, not command
ownership.

Setup advisor may improve the existing OSV recommendation when both package
metadata and a lockfile are present. It must continue to say `consider`, keep
the manual profile, and avoid selecting a package manager or constructing a
command from detected repository evidence.

## OSV Scanner V2 Input Contract

The parser accepts a JSON object with a `results` array. Each valid result may
contain:

- `source.path`: scanner-reported lockfile, SBOM, Git, or image path;
- `source.type`: normally `lockfile`, `sbom`, `git`, or `artifact` in current
  v2 models;
- `packages`: package vulnerability entries;
- `packages[].package.name`;
- `packages[].package.version`;
- `packages[].package.ecosystem`;
- `packages[].vulnerabilities`: embedded OSV advisory objects;
- `packages[].groups`: alias-equivalent vulnerability groups.

The parser also accepts an outer `packages[].version` only as a compatibility
fallback for artifacts supported by Agent Maintainer before Phase 180. The
nested v2 field wins whenever both are valid.

Malformed roots, results, sources, packages, advisories, groups, aliases,
ranges, events, or optional scalar fields are skipped locally. One malformed
neighbor must not hide valid findings in the same artifact.

## Alias Group Normalization

For each package, the parser indexes valid vulnerabilities by non-empty `id`.
When valid `groups` exist, each group becomes at most one finding:

1. Validate, deduplicate, and sort `groups[].ids`.
2. Use the first sorted group ID as the canonical advisory symbol.
3. Union the remaining group IDs, group aliases, and embedded vulnerability
   aliases into a sorted alias list, excluding the canonical ID.
4. Select the advisory whose ID matches the canonical ID for the summary when
   available; otherwise use the first referenced valid advisory.
5. Union fixed versions from every referenced advisory.
6. Preserve valid `groups[].max_severity` as display metadata.

Each valid vulnerability not referenced by a valid group becomes one fallback
finding using its own ID and aliases. This supports older or partial OSV JSON
and ensures one malformed group does not hide a valid advisory, while valid
current group data still prevents duplicate facts.

## Fixed Versions And Summary Text

OSV Scanner v2 does not provide one top-level fixed-version field. The parser
collects non-empty `fixed` values from
`affected[].ranges[].events[]` across all advisories referenced by the group,
deduplicates them, and sorts them. `last_affected` and enumerated affected
versions do not count as fixes.

Advisory summary text is whitespace-normalized and truncated to a small fixed
character limit before it enters a finding. Full advisory details, references,
CVSS vectors, database payloads, and source snippets remain available only in
the bounded artifact expansion path. Exact facts must not copy full advisory
records into model context.

## Source Path Safety

Scanner output may contain absolute machine paths even when the scan began at a
repository root. The parser therefore separates a fact path from a display
label:

- A normalized relative path with no Windows drive, root, `.` identity, or
  parent traversal may become the fact `path`.
- An absolute, drive-qualified, empty, or parent-traversal path never becomes a
  fact `path`.
- For an unsafe path, the display label may retain only a safe final filename
  such as `package-lock.json` or `pnpm-lock.yaml`.
- If no safe filename exists, the display label is `<unknown source>`.

The parser does not inspect the current working directory, guess a repository
root, walk the filesystem, or convert absolute paths heuristically. This keeps
the reusable parser deterministic and prevents local machine paths from
entering compact summaries, exact context, fixtures, or documentation.

## Normalized Finding And Fact Shape

The parser owns an immutable typed finding with these fields:

- safe relative `path` or `None`;
- safe source label and source type;
- ecosystem, package name, and installed version;
- canonical advisory ID;
- sorted aliases and fixed versions;
- optional max severity and bounded summary.

The exact fact uses:

- `check`: the original `osv-scanner` check name;
- `path`: the safe relative source path or `None`;
- `line` and `column`: `None`;
- `symbol`: canonical advisory ID;
- `severity`: `error`;
- `message`: concise package, advisory, aliases, fixes, source, severity, and
  summary details, omitting empty clauses.

The message order is stable. It never includes absolute paths, advisory detail
bodies, reference URLs, scanner logs, or package-manager command suggestions.

## Bounds And Determinism

Normalized findings are sorted before retention by:

1. safe source label;
2. ecosystem;
3. package name;
4. installed version;
5. canonical advisory ID.

The parser retains at most 500 findings from one artifact. Compact verifier
output renders at most 50 total lines and adds the existing omission marker.
Exact context retains the existing five-fact-per-check limit. Sorting happens
before every limit so input order cannot change retained findings.

## Shared Parser Boundary

Add a focused `agent_repair_facts.parsers.osv_scanner` module that depends only
on `agent_repair_facts.payloads` and the standard library. It owns decoded JSON
validation, normalized findings, alias grouping, fix extraction, path safety,
ordering, bounds, and exact fact rendering.

`agent_repair_facts.registry` maps the existing `osv-scanner` artifact name to
the new exact fact parser. `agent_maintainer.core.structured_security` imports
the normalized parser for compact rendering and removes its separate OSV schema
walk. The explicit Tach edges are recorded in the colocated domain files and an
architecture decision explains why this inward dependency prevents schema
drift without expanding scanner ownership.

## Data Flow

```text
configured global osv-scanner command
  -> .verify-logs/osv-scanner.json
  -> shared OSV v2 parser
     -> sorted, safe, grouped findings (max 500)
        -> compact failed-check summary (max 50 lines)
        -> exact repair facts (existing max 5 per check)
```

Artifact reads remain governed by the existing bounded exact-fact read budget.
The parser performs no subprocess, network, filesystem discovery, or artifact
write.

## Exit And Error Semantics

- OSV Scanner exit status remains authoritative.
- A vulnerability-result exit remains a failed check even if parsing yields no
  facts.
- Invalid JSON, a non-object root, a missing or non-array `results`, or an
  unsupported shape yields no structured summary and no exact facts.
- The normal bounded raw log and explicit artifact expansion command remain the
  fallback.
- An empty valid result produces no facts and no vulnerability summary.
- Parser errors never convert scanner failure to success or scanner success to
  failure.

## External Compatibility Evidence

Phase 180 reuses two public repositories already pinned by the TypeScript
maturation evidence:

1. `vitest-dev/eslint-plugin-vitest` at
   `7c697f8a53d7d7551b00ef11217d58cd45a0cf7d`, covering pnpm 10 and lockfile
   format v9.
2. `jsynowiec/node-typescript-boilerplate` at
   `550dfd2a976d69254ed71eb6f5a6c5ee20060807`, covering npm and
   `package-lock.json` format v3.

Capture each repository from an exact detached commit without installing
dependencies. Record repository URL, full commit, relative lockfile path and
hash, package-manager declaration, scanner version, capture command, UTC
collection time, scanner exit code, and raw report SHA-256.

Raw reports may contain large embedded advisory bodies and absolute temporary
paths. Store them only in temporary local capture space. Commit a deterministic
bounded projection containing every field the parser consumes, with source
paths normalized to repository-relative values. Record the raw report hash and
projection method so evidence remains auditable without committing machine
paths or oversized advisory payloads.

Tests never clone repositories, install dependencies, query OSV, or require an
`osv-scanner` binary. A synthetic fixture defines edge behavior; public capture
projections provide compatibility evidence.

## Testing

Focused tests will prove:

- current v2 nested package identity and source fields;
- legacy outer-version compatibility with nested precedence;
- one fact per valid alias group;
- groupless vulnerability fallback;
- deterministic alias and fixed-version ordering;
- fix extraction from OSV range events only;
- safe relative paths and absolute/traversal redaction;
- bounded advisory summaries;
- malformed roots and malformed neighbors do not raise;
- sorting before the 500-finding parser limit;
- compact rendering and omission behavior at 50 lines;
- existing five-fact context retention;
- registry dispatch for `osv-scanner` artifacts;
- current compact summary behavior uses nested v2 versions;
- pinned npm and pnpm projections contain no temporary or user paths;
- setup guidance remains optional/manual and evidence-based;
- docs and DocSync claims remain current;
- Tach and architecture-decision checks pass.

## Documentation And Roadmap

- Add Phase 180 to the full roadmap blueprint and a focused phase document.
- Mark OSV dependency facts complete in the TypeScript/React parity roadmap and
  name package-manager audit facts as the next slice.
- Update TypeScript provider and provider-status docs to explain that OSV uses
  the global optional gate rather than a TypeScript command.
- Update supported scan/tool guidance only where the new exact-fact behavior is
  user-visible.
- Extend DocSync evidence and attest reviewed-but-unchanged claims where
  required.
- Keep TypeScript/JavaScript experimental in every public status statement.

## Alternatives Considered

### Add a TypeScript-specific OSV command

Rejected. The existing OSV check already scans mixed-ecosystem lockfiles and
owns binary, profile, output, and exit semantics. A provider-local command would
duplicate configuration and make the same scanner behave differently by
ecosystem.

### Add facts without sharing the summary parser

Rejected. This is the smallest edit, but the current compact summary already
demonstrates schema drift by reading the legacy outer version. Two parsers would
make future OSV changes inconsistent across repair surfaces.

### Combine OSV and package-manager audits

Rejected for Phase 180. npm, pnpm, Yarn, and Bun audit formats and exit behavior
are separate contracts. The roadmap explicitly sequences lockfile-aware OSV
facts before package-manager-specific audit summaries.

### Preserve absolute scanner source paths

Rejected. Exact local paths improve precision but leak machine information into
summaries, fixtures, and context. Root guessing would add hidden filesystem
state to a reusable parser. Safe relative paths plus filename-only labels are a
more reliable first boundary.

### Emit one fact per embedded advisory

Rejected. OSV Scanner v2 supplies groups specifically to unite alias-equivalent
records. Per-advisory facts would duplicate one vulnerability as CVE, GHSA, and
ecosystem IDs and waste the five-fact context budget.

## Acceptance Criteria

- The existing `osv-scanner` check emits exact, bounded repair facts from valid
  v2 artifacts.
- Alias-equivalent advisories produce one deterministic fact.
- Nested v2 package versions appear in facts and compact summaries.
- Fixed versions come only from valid OSV `fixed` range events.
- Absolute and traversal source paths never enter fact paths or rendered text.
- Malformed inputs never raise and preserve normal fallback behavior.
- The existing command/config/profile/exit boundary is unchanged.
- Public npm and pnpm projections are pinned, bounded, path-safe, and parsed in
  offline tests.
- Setup guidance remains explicit, optional, and manual-profile by default.
- TypeScript/JavaScript remains experimental.
- Focused tests, full verification, manual/security verification, DocSync,
  Tach, and hosted CI pass before merge.

## Primary References

- [OSV Scanner output documentation](https://google.github.io/osv-scanner/output/)
- [OSV Scanner v2 result models](https://github.com/google/osv-scanner/blob/main/pkg/models/results.go)
- [OSV schema](https://ossf.github.io/osv-schema/)
- `docs/roadmap/typescript-react-parity-roadmap.md`
- `src/agent_maintainer/catalogs/security.py`
- `src/agent_maintainer/core/structured_security.py`
- `src/agent_repair_facts/parsers/security.py`
