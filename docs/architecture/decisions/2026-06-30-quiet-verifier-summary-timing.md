# ADR: Quiet Verifier Summary Timing

## Status

Accepted.

## Context

Phase 58 makes terminal verifier output explicitly summary-first. The output
contract includes pass/fail status, profile, run id, duration, expected profile
hint, failed checks, expansion commands, and run-scoped log directory.

Run duration already lives in `agent_maintainer.verify.timing` for diagnostic
artifacts. Duplicating timing formatting in `core.reporting` would mix verifier
semantics into a generic reporting helper, while duplicating it in
`result_summary` would drift from manifest timing behavior.

## Decision

Allow `agent_maintainer.verify.result_summary` to depend on
`agent_maintainer.verify.timing`. `result_summary` remains the verifier-specific
adapter that turns check results into terminal run details. `core.reporting`
continues to print already prepared compact lines and does not compute verifier
timing.

## Consequences

Terminal and manifest timing stay aligned through one timing module. Raw command
logs remain in run-scoped artifacts; this change only affects the compact
summary lines shown to agents.
