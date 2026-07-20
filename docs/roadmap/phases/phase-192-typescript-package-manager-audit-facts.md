# Phase 192: TypeScript Package-Manager Audit Facts

## Status

Status: complete on 2026-07-20.

## Objective

Provide explicit, normalized, bounded package-manager audit facts for the
experimental TypeScript/JavaScript provider while preserving repository-owned
command execution and advisory-only maturity.

## Delivered

- Root and workspace configuration for an explicit manager, command, and
  `full`/`ci` profile selection.
- Supported manager keys for npm, pnpm, Yarn, and Bun with no manager inference.
- Shared JSON/NDJSON adapters and one normalized contract for exact facts and
  compact summaries.
- Manifest, artifact, failure-record, and context transport for the parser hint
  plus explicit manager context.
- Deterministic ordering, deduplication, safe-path handling, malformed-neighbor
  recovery, clean-report handling, and truthful bounded omissions.
- Synthetic fixtures for every supported manager, malformed input, unsafe paths,
  clean output, and parser/summary retention limits.
- Offline pinned public projections with canonical report hashes for npm
  `jsynowiec/node-typescript-boilerplate` and pnpm
  `vitest-dev/eslint-plugin-vitest`.

## Contract boundary

The configured `typescript_package_manager_audit_manager` and exact
`typescript_package_manager_audit_command` are executed unchanged and the
process exit status is preserved. A non-empty vulnerability result is advisory
evidence; it does not enable a blocking security or reviewability gate.
Yarn and Bun remain fixture-only until equivalent public evidence is collected.

The parser retains at most 500 findings, 25 list values, 200-character scalar
fields, and 500-character paths. Compact summaries retain at most 50 summary lines.
Unsafe paths may remain as safe display labels but never become context targets.

## Implementation commits

- `286a110` — configure TypeScript package-manager audits;
- `25a85dc` — normalize package-manager audit facts and adapters;
- `5e4df19` — reuse structured audit facts across summaries and context;
- `4064900` — add pinned npm/pnpm projection replay tests.

## Verification evidence

Focused configuration, parser, summary, transport, and projection tests pass;
Ruff, Pyright, Tach, and Archguard pass on the changed implementation. The
post-documentation full verification body passed 3,148 tests with 11 skips and
92.71% coverage. Contract compatibility is qualified by the `0.1.0b14`
candidate bump; hosted release evidence is recorded separately after the
protected publication flow.
DocSync recognizes the new audit evidence anchors; its check still reports 26
stale historical attestations from earlier changes, which were not rewritten.

TypeScript/JavaScript remains experimental. The next parity slices are
generated-file/framework policy evidence, declared Nx boundaries, mutation
facts, and a blocking-gate promotion assessment.
