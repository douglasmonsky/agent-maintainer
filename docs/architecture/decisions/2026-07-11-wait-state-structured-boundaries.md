# 2026-07-11: Wait State Structured Boundaries

## Status

Accepted.

## Context

Wait orchestration consumes JSON from private daemon files, GitHub CLI output,
and cached verifier metadata. Runtime container checks did not give strict
Pyright visibility into keys or array elements. Malformed neighboring GitHub
jobs and checks must remain isolated, while invalid root run output should fail
with an actionable error rather than an incidental attribute failure.

The wait package is application infrastructure and may depend inward on the
existing dependency-free `agent_maintainer.core.structured_values` boundary.

## Decision

Daemon envelope and heartbeat readers, GitHub run and PR parsers, and the
cached-verifier fallback normalize decoded JSON through
`agent_maintainer.core.structured_values`. GitHub arrays retain valid job and
check objects while ignoring malformed neighbors. A non-object GitHub run root
raises `ValueError`; daemon and cached-verifier readers keep their existing safe
fallback behavior for malformed state.

The corresponding dependency edges are recorded in
`src/agent_maintainer/wait/tach.domain.toml`.

## Consequences

Wait-state data crosses an explicit runtime boundary before orchestration code
uses it. Pyright, IDEs, and future agents can follow string-keyed mappings and
object arrays without reconstructing implicit JSON shapes. Corrupt optional
state remains non-fatal, while a violated GitHub command contract is reported
clearly.

No external dependency, suppression, cast, or permissive `Any` annotation is
introduced. Domain packages remain isolated from wait infrastructure, and the
new edges point only inward to a core validation utility.

## Alternatives Considered

- Duplicate guards in each wait module. Rejected because the repository already
  owns a tested provider-neutral structured-value boundary.
- Cast decoded payloads or suppress strict diagnostics. Rejected because those
  approaches would conceal malformed external or persisted data.
- Reject every malformed nested record. Rejected because one malformed
  neighboring GitHub record should not hide otherwise actionable failures.

## Verification

Mapped tests cover a non-object GitHub run, malformed neighboring GitHub jobs
and PR checks, malformed cached-verifier metadata, and daemon state fallbacks.
Tach, Ruff, strict Pyright, file and change budgets, the broad local verifier,
and hosted CI enforce the boundary.
