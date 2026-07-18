# Share OSV parsing across repair facts and core summaries

## Status

Accepted on 2026-07-17.

## Context

Agent Maintainer consumes the same OSV Scanner v2 artifact in two places:
exact repair facts and compact failed-check summaries. The original core
summary had its own partial decoder. That decoder used the legacy outer
package version, emitted aliases as duplicate vulnerabilities, and did not
apply the path-safety rules required for repair facts.

## Decision

`agent_repair_facts.parsers.osv_scanner` owns validation and normalization of
OSV Scanner artifacts. It returns bounded normalized findings plus the total
supported finding count. Both repair facts and core summaries consume that
result, and the core layer owns only its display limit and omission message.

The dependency points from `agent_maintainer.core.structured_security` to the
parser module. The parser remains independent of the core reporting layer, so
normalization cannot depend on presentation or execution concerns.

## Consequences

- Nested package versions, alias groups, fix events, and safe source labels
  have one interpretation.
- Summary output and repair facts can have different retention limits without
  parsing the artifact twice in one call site.
- Changes to supported OSV shapes must update the shared parser tests.
- This boundary is specific to OSV. Other structured-security formats remain
  local until sharing removes demonstrated duplication.

## Alternatives considered

Keeping two parsers would preserve package boundaries but retain divergent
security semantics. Moving all structured-security parsing into the repair
facts package would create a broad abstraction before the other formats need
it. A narrow one-way dependency is the smallest change that removes the known
duplication.
