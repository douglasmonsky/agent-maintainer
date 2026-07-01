# Structured Artifact Summary Boundary

## Status

Accepted.

## Context

Verifier repair output now needs compact summaries for several structured
artifacts beyond Ruff, Pyright, and Bandit. Keeping all artifact parsing in
`agent_maintainer.core.reporting` would make the reporting module a grab bag of
JSON/XML parsers and push it toward the file-size and cohesion limits the
project is trying to enforce.

## Decision

Add `agent_maintainer.core.structured_artifacts` as the parser boundary for
tool-specific structured artifact summaries. `agent_maintainer.core.reporting`
keeps the existing public helper and delegates expanded artifact formats to the
new module.

The Tach contract allows `core.reporting` to depend on
`core.structured_artifacts`; the new parser module has no internal package
dependencies.

## Alternatives Considered

- Keep all parsers in `core.reporting`. Rejected because it would weaken module
  cohesion and make future parser additions harder to review.
- Put parsers under `verify`. Rejected because summaries are consumed by core
  executor reporting before run-scoped verification artifacts are assembled.

## Remains Forbidden

- Structured summaries must not print raw secret values from scanner artifacts.
- Parser failures must fall back to existing raw-output summaries instead of
  failing verification.
- Adding a parser must not require a new scanner or public profile.
