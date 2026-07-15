# Verifier Partial Manifest Boundary

- Status: accepted
- Date: 2026-07-15
- Scope: parallel verification orchestration and artifact ownership

## Context

The verifier executed every check sequentially in one process. Splitting CI at
the workflow layer alone would duplicate check-selection policy and could merge
results from different commits, configurations, references, or check sets.

## Decision

Agent Maintainer owns immutable verifier groups and records grouped runs as
partial manifests. Each partial identifies its profile, group, HEAD, base ref,
compare branch, configuration hash, and selected check names. The
`agent_run_artifacts` package owns deterministic aggregation because combining
already-produced artifacts does not require verifier configuration or check
execution.

Aggregation fails closed when groups are missing or duplicated, identities or
thresholds differ, selected checks do not match the manifest, check names occur
more than once, or any check has a failed or unknown status. The aggregate
orders groups and checks by the declared group contract rather than artifact
download order.

Normal verifier invocations remain sequential. Grouped execution and
aggregate-only operation require explicit CLI options, and group identity is
part of same-state result reuse.

## Consequences

- Workflow jobs can run verifier-owned partitions without reimplementing check
  lists in YAML.
- A newly introduced catalog check must be assigned deliberately before grouped
  CI can pass.
- Aggregate-only jobs need no project dependencies beyond the installed Agent
  Maintainer package and downloaded partial manifests.
- Partial artifacts are evidence for one exact selection, not interchangeable
  caches for other groups or repository states.
