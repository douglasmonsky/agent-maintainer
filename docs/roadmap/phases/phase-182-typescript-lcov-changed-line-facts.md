# Phase 182: TypeScript LCOV Changed-Line Facts

Status: complete

## Goal

Combine existing LCOV parsing and Git changed-line mapping into a bounded,
advisory TypeScript/JavaScript coverage report before considering any threshold
or blocking provider promotion.

## Scope

- Add `test-intel typescript-coverage` for an existing LCOV artifact.
- Support explicit Git base/staged selection and workspace source roots.
- Report weighted aggregate and deterministic per-file executable changed-line
  coverage facts.
- List changed source missing from LCOV separately.
- Confine artifacts and source paths to the repository and bound input/output.
- Preserve reusable LCOV parsing in `agent_repair_facts` and Git-aware
  orchestration in `agent_maintainer.test_intel`.
- Replay bounded projections from two pinned public committed LCOV artifacts.

## Non-Goals

- No Jest, Vitest, Istanbul, V8, npm, pnpm, Yarn, or Bun execution.
- No package-manager, workspace, test-runner, command, or reporter inference.
- No `diff-cover` subprocess or change to Python coverage enforcement.
- No threshold, baseline, ratchet, verifier profile, configured provider check,
  or blocking TypeScript gate.
- No generated-file/framework policy, package-manager audit, Nx, React lint, or
  mutation work.

## Public Evidence

The offline compatibility fixtures retain verbatim record projections and full
artifact fingerprints from:

- `CMSgov/qpp-measures-data` at
  `b2dd1ed84ed4da08269a4d0d625711d57688523d`: npm, TypeScript, Jest V8
  coverage, explicit `jest:cov` script, committed `lcov.info`;
- `starbeamjs/starbeam` at
  `9a60f092c68946007e8024c0d4e46ccd3e724a51`: pnpm workspace and committed
  Istanbul-compatible `coverage/lcov.info`.

The Starbeam revision does not declare the historical committed artifact's
exact generation command. The fixture records that limitation rather than
attributing its current Vitest version to older coverage data. Synthetic
fixtures remain authoritative for malformed input, bounds, path safety,
workspace mapping, Git selection, and percentage semantics.

## Acceptance Criteria

- Root and workspace-relative LCOV sources map only to safe repository paths.
- Aggregate coverage uses total covered/executable changed lines, not an
  average of per-file percentages.
- Missing LCOV evidence stays visible and outside the executable denominator.
- Duplicate records/lines count once and any positive hit wins.
- Zero executable changed lines reports unknown, not synthetic 0% or 100%.
- Text and JSON are deterministic, bounded, and explicitly advisory.
- Existing TypeScript repair facts and Python coverage behavior stay compatible.
- TypeScript/JavaScript remains experimental.

## Verification

Run focused parser, adapter, CLI, external fixture, existing TypeScript
structured-fact, documentation, Tach, Archguard, Ruff, Pyright, and DocSync
checks, followed by a fresh full verifier and hosted CI.
