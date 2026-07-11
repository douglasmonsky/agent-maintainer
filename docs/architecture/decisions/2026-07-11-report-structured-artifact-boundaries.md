# 2026-07-11: Report Structured Artifact Boundaries

## Status

Accepted.

## Context

Static report generation consumes verifier manifests, check records, technical
debt categories, threshold maps, and string arrays from JSON artifacts. Runtime
container checks preserved defensive rendering but left nested keys and elements
unknown to strict Pyright.

The report package is application code and may depend inward on the existing
dependency-free `agent_maintainer.core.structured_values` boundary.

## Decision

`report.html`, `report.sections`, and `report.tables` normalize decoded objects
and arrays through `agent_maintainer.core.structured_values`. The dependency
edges are recorded in `src/agent_maintainer/report/tach.domain.toml`.

Manifest loading exposes a string-keyed object. Check arrays and debt-category
arrays retain only valid string-keyed objects, threshold maps require string
keys, and string-list rendering traverses an explicit `list[object]` boundary.

## Consequences

Malformed neighboring checks, categories, and list entries are isolated without
obscuring valid report data. Non-object manifests continue to fail with the same
clear error. HTML content and escaping behavior remain unchanged.

Pyright, IDEs, and future agents can follow report artifact shapes from loading
through rendering. No dependency, suppression, or permissive type was added.

## Alternatives Considered

- Cast each report container. Rejected because these values originate in
  external artifacts and require runtime validation.
- Duplicate report-local normalizers. Rejected because application core already
  owns the provider-neutral structured-value boundary.
- Convert every report artifact into new dataclasses. Rejected because these
  small read-only views do not justify a second domain model.
- Reject a whole report when one nested entry is malformed. Rejected because it
  would weaken the established fault-isolation behavior.

## Verification

Mapped HTML tests cover malformed checks, debt categories, and artifact-list
neighbors while asserting valid sections, links, and escaped failure text still
render. Tach, Ruff, strict Pyright, file and change budgets, the broad verifier,
and hosted CI enforce the boundary.
