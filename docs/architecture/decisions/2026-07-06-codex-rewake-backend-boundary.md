# Codex Rewake Backend Boundary

## Status

Accepted.

## Context

Background wait sweepers can now move GitHub PR waits to terminal state without
foreground polling. Codex still needs an explicit continuation surface before a
background watcher can resume roadmap work automatically.

## Decision

Add `agent_maintainer.wait.codex_rewake` as an optional wait-layer adapter.
`agent_maintainer.wait.cli` may call it after `sweep --watch` reaches terminal
state. The adapter is inactive unless `AGENT_MAINTAINER_CODEX_REWAKE=1` is set.

## Boundary

The rewake adapter may inspect Codex thread metadata from process environment and
dynamically import the optional `openai-codex` SDK. It must not persist thread
ids, SDK prompts, hook stdin, API keys, or other private payloads in wait
records. If SDK import, auth, thread metadata, or resume fails, the wait stays
`ready_for_manual_resume` and the existing `wait resume <id>` command remains the
recovery path.

## Alternatives Considered

- Add a hard `openai-codex` dependency. Rejected because background waits should
  remain installable without Codex SDK users pulling beta SDK/runtime packages.
- Put SDK rewake in the hook. Rejected because terminal state belongs to the
  watcher path, not the PR-create lifecycle hook.
- Persist the Codex thread id in wait records. Rejected to keep durable wait
  records free of client-session metadata.

## Consequences

Codex can opt into automatic continuation when the SDK and thread metadata are
available, while existing manual resume behavior remains the default and fallback
for every environment.
