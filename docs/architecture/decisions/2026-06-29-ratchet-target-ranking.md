# ADR: Ratchet Target Ranking

## Context

Phase 14 needs the ratchet baseline status model to produce a small, actionable
repair queue. Agents should see which legacy issue to work on next without
expanding the whole baseline or large files into context.

## Decision

Add `agent_maintainer.ratchet.ranking` and
`agent_maintainer.ratchet.reporting` to the runtime layer in `tach.toml`.
Ranking consumes `RatchetStatusReport` entries and returns bounded repair
targets with a reason, current metric summary, score, and first safe context
command.

The first ranking policy is intentionally deterministic:

- prioritize `new` before `worsened`, then unchanged/improved findings.
- boost findings whose path appears in the current Git diff.
- exclude resolved findings from target output.
- break ties by path and check name.

## Alternatives Considered

A richer planner could inspect nearby failing tests, type errors, and dependency
impact immediately, but that would make the first ranking pass depend on several
unrelated artifacts. The roadmap keeps those as later inputs so this phase can
land the stable target shape first.

## Consequences

Future phases can add more scoring signals without changing the `ratchet next`
output contract. Ranking must remain bounded and explain why a target was chosen.
