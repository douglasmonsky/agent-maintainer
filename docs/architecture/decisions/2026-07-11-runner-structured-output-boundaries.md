# 2026-07-11: Runner Structured Output Boundaries

## Status

Accepted.

## Context

The Bandit, Ruff, Pyright, and Mutmut runners decode JSON produced by external
tools. Runtime container checks established only that decoded values were
dictionaries or lists, leaving their keys and elements unknown to strict
Pyright. Bandit and Ruff output can also contain malformed neighboring entries
that should not prevent valid diagnostics from being reported.

The runner package is application infrastructure and may depend inward on the
existing dependency-free `agent_maintainer.core.structured_values` boundary.

## Decision

The four runners normalize decoded JSON objects and arrays through
`agent_maintainer.core.structured_values` before inspecting them. Bandit and
Ruff retain raw valid artifacts while filtering malformed diagnostic entries;
Pyright validates its nested summary object; Mutmut validates the root object
before converting counters to its typed domain object.

The corresponding dependency edges are recorded in
`src/agent_maintainer/runners/tach.domain.toml`.

## Consequences

External tool output crosses one runtime-validated boundary before runner logic
uses it. Pyright, IDEs, and future agents can follow explicit string-keyed
mappings without reconstructing implicit JSON shapes. Valid Bandit and Ruff
findings remain actionable even when adjacent entries are malformed.

No external dependency, suppression, cast, or permissive `Any` annotation is
introduced. Domain code remains isolated from runner infrastructure, and the
runner package gains only an inward dependency on a core validation utility.

## Alternatives Considered

- Duplicate local type guards in each runner. Rejected because the repository
  already owns a tested provider-neutral structured-value boundary.
- Cast decoded payloads or suppress strict diagnostics. Rejected because those
  approaches would conceal malformed external data instead of validating it.
- Introduce runner-specific dataclasses for every external schema. Rejected as
  unnecessary for the small set of fields consumed at these boundaries.

## Verification

Mapped tests cover malformed neighboring Bandit and Ruff records and an invalid
Pyright summary. Existing Mutmut tests cover valid and invalid counter values.
Tach, Ruff, strict Pyright, file and change budgets, the broad local verifier,
and hosted CI enforce the boundary.
