# Pinned public LCOV projections

These fixtures retain small, verbatim record projections from public LCOV files
committed at exact Git revisions. The full public files are represented by
their Git blob identifiers, SHA-256 hashes, and byte counts; the repository
does not vendor the complete reports.

`cmsgov-qpp-measures-data.json` is an npm/TypeScript/Jest V8 coverage shape with
an explicit producing script. `starbeam-pnpm-workspace.json` is a pnpm workspace
with an Istanbul-compatible committed LCOV shape. Starbeam does not declare the
historical artifact's exact generating command at the pinned revision, so the
fixture records that limitation instead of attributing the current Vitest
dependency to an older committed report.

The projections are compatibility evidence, not the normative parser contract.
Synthetic tests own malformed input, path rejection, duplicate records, bounds,
Git diff selection, and percentage semantics. Tests replay these fixtures
offline and never download repositories or execute their scripts.
