# Phase 181: TypeScript Dependency-Cruiser Facts

## Status

Status: complete on 2026-07-18.

## Objective

Add explicit TypeScript dependency-cruiser checks and turn documented
cruise-result JSON into deterministic, path-safe repair facts and compact
summaries without inventing repository architecture rules.

## Scope

- Add root `typescript_dependency_cruiser_command` and
  `typescript_dependency_cruiser_profiles` configuration.
- Add workspace-owned dependency-cruiser commands with stable suffixed check
  names.
- Parse only `summary.violations` from cruise-result JSON.
- Preserve supported rule names, severities, violation types, sources, and
  display-only targets.
- Reuse one normalized parser result for exact facts and compact summaries.
- Record offline npm and pnpm public compatibility projections.

The default profiles are `full` and `ci`. Empty command arrays remain optional
skips. Agent Maintainer never infers npm, pnpm, Yarn, Bun, Corepack, or Nx
commands; appends output flags; installs the tool; generates configuration;
invents rules; or changes the configured process exit status.

## Architecture Boundary

For TypeScript/JavaScript, dependency-cruiser is the Tach-like boundary-rule
tool for this phase. It does not replace Python Tach, Archguard architecture
decision policy, or declared Nx project boundaries.

The reusable `agent_repair_facts` package owns dependency-cruiser validation
and normalization. Core summary rendering imports that parser in one direction,
while the TypeScript provider owns command execution only. No provider code
imports core orchestration. The Tach domain changes are covered by an accepted
architecture decision note.

## Safety And Bounds

A valid result contains object `summary` with array `summary.violations`.
Malformed neighbors, ignored rules, unknown severities, and unsupported types
are skipped independently. Supported severities are `error`, `warn`, and
`info`; supported types are dependency, module, reachability, cycle,
instability, and folder.

Only safe repository-relative source paths become context targets. Absolute,
drive-qualified, traversal, control-bearing, dot, empty, and overlong paths are
non-targetable. Safe basenames remain available for bounded display when
possible; targets are always display-only.

The parser sorts before retaining 500 normalized findings. Failed-check
summaries contain at most 50 total lines, reserving the last line for a truthful
omission count. Context packs keep five facts per failed check. Scalars are
capped at 200 characters, targetable paths at 500 characters, and rendered
messages at 1,000 characters.

## Public Evidence

Dependency-cruiser 17.0.2 captured two pinned public repositories with reviewed
repository-specific TypeScript globs, without installing repository
dependencies or running package scripts:

- `decentralized-identity/dwn-sdk-js` at
  `0e903014464388bcfcdcd42da74c40fdd902fd23`, using npm,
  `package-lock.json`, and `.dependency-cruiser.cjs`;
- `hicommonwealth/commonwealth` at
  `fca71cca527b490e3f3ad955044a0506139d0330`, using pnpm,
  `pnpm-lock.yaml`, `pnpm-workspace.yaml`, and `.dependency-cruiser.cjs`.

The captures contained 657 and 52 parser-supported findings respectively.
Each committed projection retains the first 25 normalized violations and
records repository, revision, UTC collection time, Node and tool versions,
exact command, exit status, config and lockfile hashes, and the raw report hash
and byte count. Tests replay the projections offline without network access or
dependency-cruiser.

## Acceptance Criteria

- Root and workspace commands remain explicit and profile-controlled.
- Supported cruise-result violations produce deterministic exact facts.
- Summary, parser, context, scalar, path, and message bounds have tests.
- Unsafe sources never become context targets or expose local checkout roots.
- Exact Tach and Archguard decision checks pass.
- Both pinned public projections replay through the shared parser.
- TypeScript/JavaScript remains experimental and advisory.

## Completion Notes

Phase 181 dependency-cruiser architecture facts are complete. This deliberately
advances the architecture slice before the previously listed audit slice; it
does not promote the provider or make architecture checks blocking.
Package-manager audit facts are the next parity slice. Declared Nx boundaries,
changed-line coverage, mutation, broader security, and blocking reviewability
remain later roadmap work.
