# Mutmut Target Ratchet Check Boundary

## Status

Accepted.

## Context

The repository enabled Mutmut in the manual profile but had a single
`[tool.mutmut].only_mutate` target. That made mutation testing cheap, but too
easy to mistake for broader mutation coverage. We need a cheap ratchet that
keeps explicit mutation targets from shrinking while actual mutation execution
remains manual and release-oriented.

## Decision

Add `agent_maintainer.checks.mutmut_targets` as a focused check module under
the checks domain. The module validates `[tool.mutmut].only_mutate` count and
path-like target existence when `[tool.agent_maintainer].mutmut_target_min` is
above zero. Catalog wiring runs this check in `full` and `ci`; it does not run
Mutmut.

## Alternatives Considered

Expanding the existing Mutmut runner was rejected because runner code should
execute Mutmut, not parse project policy. Putting the check under test
intelligence was rejected because advisory target suggestions should stay
separate from verifier pass/fail policy.

## Still Forbidden

Do not treat the target-count ratchet as proof of full mutation coverage. Do
not move actual mutation execution into normal precommit/full verification.
Mutation execution stays in `manual`; this check only prevents silent target
list regression.
