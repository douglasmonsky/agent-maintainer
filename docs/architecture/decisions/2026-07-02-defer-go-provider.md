# Defer Go Provider From Active Architecture

## Status

Accepted.

## Context

Agent Maintainer briefly carried an experimental Go provider to keep the
ecosystem-provider seam from becoming TypeScript-specific. That helped validate
that provider metadata, classification, doctor rows, and advisory reviewability
should not assume Node package-manager concepts.

There are no public Go adopters yet. Keeping Go active now adds config, docs,
tests, doctor, and Tach maintenance cost while TypeScript/JavaScript is the
chosen first serious non-Python maturity track.

## Decision

Remove Go from the active provider registry, config schema, doctor rows,
classification dispatch, suppression dispatch, and Tach provider contracts.
Keep historical roadmap and ADR context so a future Go provider can be designed
from the stabilized provider patterns rather than revived from stale branch
code.

`go.mod` may remain generic repository evidence for dependency/security
recommendations, but it must not imply active Go provider support.

## Consequences

- Active provider metadata now contains Python and TypeScript/JavaScript only.
- TypeScript/JavaScript remains the first non-Python provider maturation target.
- Go can return later as a new phase with fixtures, doctor rows, explicit
  commands, and advisory evidence.
- The provider seam no longer gets ongoing Go canary coverage in main; this is
  acceptable because keeping unused Go code active would be higher maintenance
  tax than value at this stage.

## Alternatives Considered

- Keep Go active as a thin canary. Rejected because it still creates product and
  maintenance surface while TypeScript evidence is the priority.
- Move Go to a long-lived branch. Rejected because branch code would stop
  receiving normal CI and likely rot.
- Delete all historical Go references. Rejected because the old phase and ADR
  explain why the provider seam was tested against a non-Node ecosystem.
