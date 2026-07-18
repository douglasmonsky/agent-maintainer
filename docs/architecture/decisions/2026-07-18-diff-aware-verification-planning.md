# Diff-Aware Verification Planning Boundary

## Status

Accepted.

## Context

Agent Maintainer's verifier executes configured profiles, but a changed file
does not currently explain which profiles, named checks, review categories, or
repository evidence apply to that diff. Sensitive paths also lack a strict,
repository-owned contract for the evidence an agent must add before merging.

This capability needs structured Git identity for renames and deletions,
provider classifications, bounded package ownership, strict policy parsing, and
the configured check catalog. Folding those concerns into verify execution or
reviewability checks would mix planning with execution and allow policy to
silently change the verifier's authoritative gates.

## Decision

Add `agent_maintainer.verification_plan` as an additive planning domain. It owns
strict versioned path-risk policy, segment-aware path matching, affected-unit
resolution, evidence evaluation, and deterministic text and JSON reports. The
existing ecosystem and catalog domains expose facts to the planner and never
depend back on it.

Read Git name-status data as NUL-delimited bytes after resolving a base ref with
`git rev-parse --verify --end-of-options`. Rule triggers include both source and
destination paths for renames and copies, and include deleted paths. Changed-
path evidence counts only current or destination paths, so deleting evidence
cannot satisfy a requirement.

Keep policy schema version 1 strict and fail closed on unknown keys, unsafe
paths, invalid glob syntax, unknown profiles, and ambiguous configured check
names. Multiple catalog entries with one logical name are allowed only when
their profile sets are disjoint, as with the existing profile-specific change-
budget variants.

The planner unions matched rule selections and recommends canonical verifier
commands, but it never executes checks or suppresses existing gates. The
optional `verification-plan-policy` catalog check invokes the public planner in
enforcement mode when `.agent-maintainer/path-risk.toml` exists.
Policy-definition changes require a decision record; implementation changes
require focused tests without imposing a new ADR on every source edit.

## Consequences

Agents and CI receive a byte-stable explanation of the exact repository units,
policy rules, evidence, checks, profiles, and review categories implied by a
diff. Required missing evidence blocks only under explicit enforcement;
advisory policy remains informative.

TypeScript workspace expansion is literal, repository-confined, and capped.
Workspace manifests are independently resolved and must remain inside the
repository even when the workspace directory itself is safe. Human-readable
output escapes control characters and caps nested changed-path lists; policy
matching uses bounded iterative state rather than recursive glob evaluation.
The root command validates configuration relative to an explicit `--target`
instead of an unrelated current directory.

Java ownership remains conservative and source-derived; the planner does not
interpret executable Gradle settings DSL. Unknown or ambiguous ownership falls
back to a repository unit with an advisory.

The planner is not a dynamic test skipper. Existing verifier profiles and
artifacts remain authoritative, and future policy schema changes require a new
version and migration tests.

## Alternatives Considered

- Put path-risk decisions inside each check. Rejected because policy would be
  scattered and impossible to audit as one repository contract.
- Let the planner execute a reduced check set. Rejected because it could hide
  regressions and turn repository advice into an unreviewed CI scheduler.
- Match only current paths. Rejected because moves and deletions could bypass
  sensitive-path policy.
- Infer Java modules by executing or interpreting Gradle settings. Rejected
  because it expands the trust boundary and makes planning non-deterministic.

## Verification

Focused tests cover strict policy loading, glob semantics, NUL-delimited Git
changes, affected units, overlapping rules, destination-only evidence,
deterministic rendering, CLI exit semantics, and catalog integration. Exact
Tach validation, strict Pyright, Ruff, DocSync, the full verifier, and hosted CI
enforce the boundary.
