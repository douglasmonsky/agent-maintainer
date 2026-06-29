# Archguard Impact Analysis Commands

## Status

Accepted.

## Context

Phase 31 adds read-only architecture impact commands to `archguard`:
`map`, `impact`, and `explain-boundary`. These commands help agents and humans
understand module ownership and dependency direction before changing code.

## Decision

Add `archguard.impact` and assign it explicitly in `tach.toml`.

The module reads `tach.toml`, resolves source files to configured module owners,
and renders compact text reports. It does not run Tach, mutate policy, edit
source files, or infer architecture from dynamic execution.

## Alternatives Considered

- Add this logic to `archguard.cli`: rejected because CLI parsing would mix
  with Tach ownership analysis.
- Depend on Tach internals directly: rejected because the command only needs
  stable configuration data and should remain easy to test with fixtures.
- Generate a graph visualization in this phase: rejected because the roadmap
  asks for textual impact commands first.

## Boundaries

Impact analysis is advisory. Tach remains the enforcement layer for dependency
violations, and Archguard decision checks remain the enforcement layer for
policy-file changes.
