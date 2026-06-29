# ADR: Ratchet Baseline Package

## Context

Phase 13 adds ratchet baselines as a new command family. The feature compares
current maintainability findings against a saved JSON baseline, so agents can
distinguish new, worsened, unchanged, improved, and resolved legacy issues.

## Decision

Add `agent_maintainer.ratchet` as an orchestration package with these module
roles:

- `models` owns JSON-safe baseline and status records.
- `findings` normalizes current file-length and structure-cohesion findings.
- `baseline` owns persistence and Git provenance.
- `status` owns comparison and stale-baseline detection.
- `cli` owns the `ratchet` command surface.

The package is explicitly assigned in `tach.toml`. It may depend on shared check
modules and core config, but existing checks should not import ratchet code.

## Alternatives Considered

The older file-length-only baseline could have been extended in place, but that
would couple a multi-check ratchet model to one check adapter. A verifier log
parser was also rejected because it would make baseline behavior dependent on
profile output instead of current repository state.

## Consequences

Ratchet baselines can grow to additional checks without changing the file-length
check compatibility path. New check adapters should normalize into
`RatchetFinding` rather than adding bespoke baseline schemas.
