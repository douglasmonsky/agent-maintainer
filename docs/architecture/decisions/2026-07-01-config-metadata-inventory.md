# Config Metadata Inventory

## Status

Accepted.

## Context

Agent Maintainer's public configuration surface now spans the dataclass schema,
TOML keys, nested diagnostics aliases, environment variables, verifier CLI
overrides, starter templates, doctor output, and documentation. Static review
identified drift across those surfaces as a release risk.

## Decision

Add `agent_maintainer.config.metadata` as a read-only inventory for
`MaintainerConfig` fields. It records TOML key paths, environment override
coverage, verifier CLI override status, docs labels, and stability level.

Keep loader behavior unchanged for this slice, but test metadata against the
real loader env maps and CLI override implementation so new fields fail loudly
when metadata is incomplete.

## Consequences

New config fields must now be deliberately classified before tests pass. This
does not add a new public command, but it creates a stable internal source for
future doctor, docs, and schema-reporting work.

## Alternatives Considered

- Generate docs directly from `MaintainerConfig` only. Rejected because the
  dataclass alone does not know env vars, CLI override coverage, or nested TOML
  aliases.
- Move loader to consume metadata immediately. Deferred to keep this PR focused
  and avoid changing config behavior while adding drift guards.
- Maintain a fully hand-written table for all fields. Rejected because the
  dataclass remains the authoritative field list and should drive coverage.

## Still Forbidden

Metadata must not become an alternate config loader. Runtime precedence remains:
defaults, mode preset, explicit TOML, environment variables, then CLI flags.
