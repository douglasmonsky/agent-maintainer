# State-Aware Verifier Lock

## Status

Accepted.

## Context

Agent hooks and manual verifier commands can overlap in the same repository.
Those runs write canonical diagnostic artifacts such as `LAST_FAILURE.md`,
scanner JSON reports, and coverage data. Overlap can produce stale or duplicate
generated artifacts on developer machines and can waste agent context.

The verifier must not reuse a result for a different repository state.

## Decision

Add `agent_maintainer.verify.locking` as the state-aware verifier lock module.
It fingerprints the requested verification by profile, refs, staged mode,
`HEAD`, staged diff hash, worktree diff hash, and `pyproject.toml` hash.

When another verifier run already completed for the same fingerprint, a later
run can reuse that exit code and canonical diagnostic artifacts. When the
fingerprint differs, the later run waits for the current lock and then runs
fresh against its own state.

Generated tool artifacts remain canonical fixed paths. Tool wrappers may remove
their own configured report path before execution when the tool otherwise
preserves prior reports with numbered filenames.

## Consequences

Overlapping identical hook/manual requests converge on one verifier result.
Changed worktree or staged content cannot inherit a pass or failure from an
older state.

Coverage data defaults to the verifier diagnostic directory while preserving an
explicit user-provided `COVERAGE_FILE`.

## Alternatives Considered

Timestamped run directories were rejected for normal hook output because agents
need a stable pointer such as `.verify-logs/LAST_FAILURE.md`.

Blind lock-result reuse was rejected because another agent may edit files while
verification is running.

Per-check locks were rejected as too much orchestration for the current problem.

## Still Forbidden

Do not reuse verifier results across different fingerprints. Do not create
numbered generated artifacts as a normal conflict-resolution strategy. Do not
hide stale generated artifacts as source changes.
