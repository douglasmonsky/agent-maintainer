# Explicit and Shared TypeScript Package-Manager Audit Facts

## Status

Accepted on 2026-07-20.

## Context

The TypeScript/JavaScript provider already exposes explicit command checks and
shared repair facts for OSV Scanner, Knip, and dependency-cruiser. Package
manager audit output is useful evidence, but npm, pnpm, Yarn, and Bun do not
share one stable report shape. A provider that guessed a manager or treated
every non-zero audit exit as an equivalent failure would silently change
repository policy and make repair context unreliable.

Audit facts also need to serve two consumers: compact failed-check summaries
and exact repair/context packets. Duplicating normalization in core reporting
and the repair-facts package would create divergent severity, path, and bound
semantics.

## Decision

Add an explicit root/workspace package-manager audit check. Configuration must
declare both:

- `typescript_package_manager_audit_manager`: exactly `npm`, `pnpm`, `yarn`, or
  `bun`;
- `typescript_package_manager_audit_command`: the repository-owned command
  array, preserved exactly for execution.

The manager is never inferred from a lockfile, `packageManager` field, command
text, Corepack metadata, workspace manifest, or executable name. Empty command
arrays are optional skips. The configured process exit status remains the
source of check pass/fail; vulnerability findings are advisory evidence and do
not create a new blocking gate.

`agent_repair_facts.parsers.typescript_package_manager_audit` owns validation,
manager adapters, path safety, deterministic ordering, deduplication, and
retention metadata. Core summary rendering and exact context facts consume that
single normalized result. The transport carries the explicit manager beside
the stable parser hint so no consumer has to infer it from output.

The normalized finding contract includes manager, workspace, package, severity,
advisory identifiers, vulnerable ranges, fixed versions, dependency
scope/directness, optional safe repository-relative path provenance, source
label, and a bounded title. Supported JSON and NDJSON records are parsed
independently; malformed neighbors are skipped, while an invalid root falls
back to the normal bounded raw output.

## Bounds and safety

- Retain at most 500 normalized findings after deterministic sorting.
- Retain at most 25 values per list, 200 characters per scalar, 500 characters
  per display path, and 1,000 characters per rendered finding.
- Compact summaries contain at most 50 total lines and report omitted findings
  truthfully.
- Absolute, drive-qualified, UNC, traversal, dot, control-bearing, empty, and
  overlong paths are display-only and never become context targets.
- Clean reports with zero findings are valid; unsupported or malformed roots are
  not treated as clean.

## Evidence

Synthetic fixtures cover npm, pnpm, Yarn, and Bun JSON/NDJSON shapes, clean
reports, malformed neighbors, unsafe paths, deterministic ordering, and all
retention bounds. Pinned public projections replay offline for:

- npm `jsynowiec/node-typescript-boilerplate` at
  `550dfd2a976d69254ed71eb6f5a6c5ee20060807`;
- pnpm `vitest-dev/eslint-plugin-vitest` at
  `7c697f8a53d7d7551b00ef11217d58cd45a0cf7d`.

Each projection records the exact command, tool/runtime metadata, exit status,
report hash and byte count, and bounded normalized findings. Yarn and Bun are
fixture-only until comparable public captures are available.

## Consequences

- Exact facts and summaries cannot drift in their interpretation of audit
  severity, path safety, or bounds.
- Explicit manager context survives manifests, failure records, artifacts, and
  replay, preventing unsafe output-based inference.
- The provider gains useful vulnerability evidence without changing command
  ownership or promoting TypeScript/JavaScript reviewability.
- New package-manager report shapes must extend the adapter and its fixtures;
  they must not be handled by a generic permissive fallback.
- Blocking audit policy, mutation, generated-file policy, and declared Nx
  boundaries remain separate roadmap slices.

## Alternatives considered

Inferring a manager from lockfiles or command names would be convenient but
would violate explicit-command ownership and fail in mixed workspaces. Running
one universal `npm audit` command would misrepresent pnpm, Yarn, and Bun
repositories. Keeping separate parsers for summaries and exact facts would
invite drift. Treating every vulnerability as a blocking reviewability gate
would exceed the provider's evidence and maturity bar.
