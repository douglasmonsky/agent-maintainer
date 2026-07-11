# 2026-07-11: Maintenance Input Boundaries

## Status

Accepted.

## Context

Scaffolding, repository checks, and change-plan parsing consume decoded JSON or
TOML at several small maintenance boundaries. Plain dictionary checks left
nested keys and values unknown to strict Pyright. Transaction result objects
also used untyped collection factories even though their element type is part
of the public result contract. Diagnostic manifests, runtime events, scoring
datasets, and async verifier state have the same decoded-data trust boundary.

Context and ratchet CLIs also annotated helpers with argparse's private
subparser action class even though they only need the public parser-creation
callable.

These modules are operationally related: they validate repository-owned
configuration or report data before planning and verification act on it.

## Decision

Scaffold planning, file-length baselines, cohesive-override event payloads,
Mutmut configuration, and change-plan metadata use the existing
`agent_maintainer.core.structured_values` helpers at decoded-data boundaries.
The corresponding dependency edges are recorded in each package's
`tach.domain.toml` contract.

Mutable result fields in scaffold transactions and hook mutations use named,
typed factory functions. Valid input behavior and public collection types stay
unchanged.

Hook audit records, verifier manifests, runtime event objects, scoring rows,
and async verifier state use the same structured-value normalization. Context
and ratchet parser helpers depend on a local public parser-factory protocol
instead of argparse's private action implementation.

## Consequences

Decoded mappings expose string keys and `object` values until local validation
narrows them. Malformed non-string keys are rejected instead of leaking into
domain configuration. Typed factories make result ownership visible without a
suppression, cast, or permissive `Any` annotation.

Pyright, IDEs, and future agents can trace these maintenance inputs from their
trust boundary to their consumers. The two production passes remove all 50
remaining source diagnostics without expanding the checked source scope; the
strict baseline now contains test-only debt.

## Alternatives Considered

- Cast decoded mappings to their expected types. Rejected because external
  JSON and TOML shapes require runtime validation.
- Add local mapping helpers in every package. Rejected because the core helper
  already provides a dependency-free, provider-neutral boundary.
- Suppress unknown collection factories. Rejected because a named typed
  factory states the contract directly.
- Keep the private argparse action annotation. Rejected because a small
  callable protocol expresses the actual dependency without coupling to a
  private standard-library implementation.
- Enable strict checks outside the maintained source scope. Rejected because
  this migration is a ratchet of the existing configured scope.

## Verification

Mapped tests cover valid scaffolding, malformed Mutmut keys, file-length
baselines, GitHub event parsing, change plans, hook mutations, doctor artifacts,
runtime events, malformed scoring rows, async state, and both CLI families.
Tach, Ruff, strict Pyright, change-plan validation, the full verifier, and
hosted CI enforce the boundary and dependency contracts.
