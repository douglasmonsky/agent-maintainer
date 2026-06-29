# Change Plan Package Boundary

## Status

Accepted.

## Context

Agent Maintainer needs a cohesive change-plan format before change-budget gates
can allow intentionally large migrations through a strict, reviewable process.

## Decision

Add `agent_maintainer.change_plan` as an application/runtime package. It owns
the markdown/TOML plan parser, validation rules, Git scope checks, starter
template rendering, and command-line adapter for `python -m agent_maintainer
change-plan`.

The package is explicitly assigned in `tach.toml` instead of being hidden under
an existing context or checks module. The parser and models are local to this
feature because the format is product-facing and will be reused by the
change-budget integration phase.

## Consequences

The package may depend on the standard library, local models, and Git scope
helpers. Verifier checks may depend on this package in the later integration
phase, but this phase does not let plans bypass enforcement.
