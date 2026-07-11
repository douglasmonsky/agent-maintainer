# 2026-07-11: Shared Structured Payload Normalization

## Status

Accepted.

## Context

Verifier reporting consumes decoded JSON from Pyright, Ruff, Bandit, coverage,
Semgrep, OSV Scanner, Gitleaks, and pip-audit. Strict typing exposed the same
boundary problem in the reporting, structured-pytest, and structured-security
modules: a runtime `dict` or `list` check does not establish the element and
key types needed by downstream code. Keeping local copies of those guards
also pushed reporting modules over their cohesion limits and invited slightly
different malformed-payload behavior.

## Decision

`agent_maintainer.core.structured_values` owns the narrow, provider-neutral
normalization primitives for decoded structured artifacts. It converts a
runtime-checked object into `dict[str, object]`, a runtime-checked array into
`list[object]`, filters an array to valid string-keyed objects, and reads a
plain non-boolean integer with an explicit fallback.

The reporting, structured-pytest, and structured-security modules may depend
on this helper module. Their domain-specific validation, formatting, limits,
and fallback behavior remain in the consuming modules. The dependency edges
are recorded in `src/agent_maintainer/core/tach.domain.toml`.

## Consequences

Decoded external data crosses one explicit typed boundary before scanner,
coverage, or diagnostic logic traverses it. Pyright, IDEs, and future agents
can follow stable object and array shapes without treating arbitrary payloads
as implicit `Any`. Malformed entries continue to fail closed or be skipped
according to each consumer contract.

The core domain gains one small module. This is accepted because it removes
three duplicate implementations, keeps the reporting modules within enforced
member limits, and creates no dependency outside the existing core domain.

## Alternatives Considered

- Keep one private copy in every consumer. Rejected because the copies were
  identical infrastructure and were already causing cohesion drift.
- Put the helpers in structured-security or structured-artifacts. Rejected
  because that would make coverage and generic reporting depend on a
  domain-specific consumer and could create import cycles.
- Silence strict diagnostics with `Any`, unchecked casts, or suppressions.
  Rejected because it would hide the external-data boundary instead of making
  it explicit and verifiable.

## What Remains Forbidden

The shared module must not acquire provider-specific schemas, formatting, or
business rules. Consumers must still validate semantic requirements such as
required fields, numeric ranges, canonical paths, and scanner-specific nested
structures. Unchecked casts, broad `Any`, and type suppressions are not an
acceptable substitute for runtime validation.

## Verification

Structured-artifact summary tests cover valid and malformed scanner,
diagnostic, and coverage payloads. Tach configuration tests enforce the new
dependency edges. Ruff, wemake, strict Pyright, manual verification, and the
CI-equivalent profile cover the shared module and all consumers.
