# Profile Overlap Guardrails

## Status

Accepted.

## Context

The priority-one cadence waste roadmap asks Agent Maintainer to stop nudging
agents into redundant broad verifier runs. Generated guidance now tells agents
to run one broad local profile by default, but guidance alone does not help when
the verifier can see recent runtime events that make a just-started profile
likely redundant.

## Decision

Add `agent_maintainer.verify.profile_overlap` as a small advisory helper. The
helper reads existing local runtime-event JSONL files, detects recent
`full`/`ci`, `security`/`manual`, or three-heavy-profile overlap, and returns a
single compact advisory string. `agent_maintainer.verify.quiet` owns when that
advisory is printed: only after a successful fresh verifier run, never as a
blocking gate.

No new config namespace or event schema is added. The helper uses existing
`runtime_events_enabled`, `runtime_events_dir`, and
`runtime_event_history_limit` fields.

## Boundary Guardrails

- `profile_overlap` may read runtime-event summaries, but it must not inspect
  raw command logs or conversation transcripts.
- `profile_overlap` must not change verifier exit codes.
- `quiet` remains the only verifier CLI surface that prints the advisory.
- Runtime-event collection remains best-effort; missing or malformed event
  files must not fail verification.
- The advisory should stay compact and action-oriented.

## Alternatives Considered

- Block redundant profile combinations. Rejected because the roadmap calls for
  gentle warnings first; users can have valid reasons to run overlapping
  profiles when profile behavior or CI-diff behavior is under test.
- Add new profile-overlap config fields immediately. Rejected because existing
  runtime-event settings are sufficient for the first advisory implementation.
