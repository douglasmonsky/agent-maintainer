# 2026-07-11: Test Intelligence Typed Boundaries

## Status

Accepted.

## Context

Test intelligence reads coverage.py JSON artifacts, registers mutation CLI
subcommands, and accumulates mutation sweep results. Coverage container checks
left nested keys and line elements unknown, mutation CLI annotations named
argparse's private subparser class, and the sweep result list had no explicit
domain type before its first append.

## Decision

Coverage objects, file records, summaries, and line arrays normalize through
`agent_maintainer.core.structured_values`. The dependency edges for
`test_intel.coverage` and `test_intel.coverage_lines` are recorded in
`src/agent_maintainer/test_intel/tach.domain.toml`.

Mutation CLI registration accepts argparse's public `add_parser` callback.
Mutation sweep execution declares its result accumulator as
`list[MutationSweepCandidateResult]` and its stop reason as `str | None`.

## Consequences

Malformed coverage files and neighboring line entries are isolated without
obscuring valid changed-line or file percentages. Mutation command behavior and
candidate execution order remain unchanged while private argparse types are no
longer part of the package contract.

Pyright, IDEs, and future agents can follow coverage and mutation result shapes
without inference from later use. No dependency, suppression, or permissive
type was added.

## Alternatives Considered

- Cast decoded coverage dictionaries and lists. Rejected because coverage files
  are external artifacts and require runtime validation.
- Add a local subparser protocol. Rejected because the public callback is the
  smaller and more tool-compatible boundary.
- Infer the sweep result list from the first append. Rejected because empty and
  early-stop executions are valid domain states.
- Add new coverage domain dataclasses. Rejected because the current read-only
  calculations do not justify a second coverage model.

## Verification

Mapped tests cover malformed file neighbors and mixed line arrays while
preserving valid changed-line percentages. Mutation CLI and sweep executor tests
cover parser registration, empty results, failure stops, and artifact output.
Tach, Ruff, strict Pyright, file and change budgets, the broad verifier, and
hosted CI enforce the boundaries.
