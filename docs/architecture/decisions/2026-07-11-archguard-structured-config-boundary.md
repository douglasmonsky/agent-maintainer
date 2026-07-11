# 2026-07-11: Archguard Structured Configuration Boundary

## Status

Accepted.

## Context

Archguard reads Tach TOML for architecture maps and configuration validation.
Runtime `dict` and `list` checks left keys and elements unknown, while the
large impact and source-discovery modules had little room for duplicate local
normalizers. Importing an application-level helper would also invert the
standalone architecture-tool boundary.

## Decision

`archguard.structured_values` owns dependency-free normalizers for decoded
string-keyed objects, arrays, object arrays, and non-empty string arrays.
`archguard.impact` and `archguard.tach_config_sources` may depend on this leaf
module. The dependency edges are recorded in `src/archguard/tach.domain.toml`.

DocSync remains independent and uses its existing local YAML boundary. Its
attestation loader now validates string-keyed record mappings before parsing,
and its mutable collection defaults are explicitly parameterized.

## Consequences

Tach configuration crosses one explicit runtime boundary before ownership,
source discovery, or module-path logic traverses it. Pyright, IDEs, and future
agents can follow stable object and array shapes without implicit unknowns.
Malformed neighboring module entries are skipped according to the existing
defensive contract.

Archguard and DocSync remain separate standalone packages with no new
cross-package dependency.

## Alternatives Considered

- Add casts in each consumer. Rejected because the nested TOML shapes require
  runtime validation and the modules were already near cohesion limits.
- Import `agent_maintainer.core.structured_values`. Rejected because Archguard
  must remain usable without the main application package.
- Share one helper between Archguard and DocSync. Rejected because that would
  couple otherwise independent governance tools for a very small primitive.
- Add suppressions or broad `Any`. Rejected because that would conceal the
  configuration boundary.

## Verification

Mapped tests cover mixed valid and malformed Tach modules, defensive source
configuration, YAML records with non-string keys, and typed DocSync defaults.
Tach, Ruff, wemake, strict Pyright, manual verification, and the CI-equivalent
profile enforce the new boundary.
