# Share dependency-cruiser parsing across facts and summaries

## Status

Accepted on 2026-07-17.

## Context

Agent Maintainer consumes dependency-cruiser cruise-result JSON in two places:
exact repair facts and compact failed-check summaries. Both consumers need the
same validation, path safety, deterministic ordering, and retention metadata.
Implementing those rules in core reporting as well as the repair-facts package
would create two interpretations of the same architecture violation.

Dependency-cruiser is the TypeScript and JavaScript boundary-rule counterpart
to Tach for this provider. It does not replace the repository's Python Tach
domains, the broader Archguard decisions, or Nx's declared project boundaries.

## Decision

`agent_repair_facts.parsers.typescript_dependency_cruiser` owns cruise-result
validation and normalization. It returns bounded normalized findings plus the
total supported finding count. Repair facts and
`agent_maintainer.core.structured_typescript` consume that result; core owns
only compact rendering limits and omission messages.

The provider owns explicit command execution only. It does not infer a package
manager, install dependency-cruiser, generate configuration, add reporter
arguments, synthesize boundary rules, or reinterpret process exit status.

The dependency direction points inward from core rendering to the reusable
repair-facts parser. No TypeScript provider code imports core orchestration.
Tach, Archguard, Nx, and dependency-cruiser remain distinct policy surfaces
with separate formats and ownership.

## Consequences

- Exact facts and summaries share severity, type, source, target, and rule
  semantics.
- Unsafe source paths can remain safely visible without becoming context
  targets.
- Summary omission counts include supported findings beyond parser retention.
- Changes to supported dependency-cruiser shapes must update the shared parser
  tests and public compatibility projections.
- Nx boundary support remains a later independent adapter rather than an
  inferred dependency-cruiser configuration.

## Alternatives considered

Keeping separate parsers would preserve local ownership but invite divergent
path and severity handling. Moving execution policy into the parser would
couple reusable evidence normalization to provider orchestration. Treating Nx,
Archguard, Tach, and dependency-cruiser as one generic architecture backend
would erase meaningful differences in scope and report contracts.
