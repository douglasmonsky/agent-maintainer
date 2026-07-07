# Codex Background Wait Enforcement

## Status

Accepted.

## Context

Foreground PR waiters kept Codex turns alive and produced repeated chat updates
while checks were still pending. That defeats the purpose of durable waits and
becomes expensive when large thread context is cached.

Codex thread automations provide heartbeat-style wakeups for work that should
return to the same conversation on a schedule. The repository cannot call the
Codex app automation tool directly from hook subprocesses, so repo code must
make foreground polling safe and hand off heartbeat prompts cleanly.

## Decision

Add `agent_maintainer.wait.broker` as the shared background registration path
for Codex-safe waits. Codex PR hooks use background registration by default, and
direct `wait github-pr` commands running inside Codex convert to background
registration unless `AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1` is set.

## Boundary

The broker may register durable wait records, start silent local watchers, and
render heartbeat prompts. It must not poll external systems in the foreground
Codex path. The Codex app heartbeat automation remains outside the repository
boundary; repo code exposes the prompt and wait id, while the app owns scheduling
and thread wakeup.

## Alternatives Considered

- Keep foreground `wait github-pr` as the normal Codex path. Rejected because it
  causes repeated chat turns while pending.
- Let each hook or CLI command implement its own background registration.
  Rejected because the heartbeat handoff and override policy need one owner.
- Require Codex SDK rewake for continuation. Rejected as the primary path
  because SDK auth and method availability are optional, while thread
  automations are the documented app heartbeat primitive.

## Consequences

Long-running Codex PR waits now have a mechanical guardrail against chatty
foreground polling. Future wait kinds can reuse the broker before adding their
own heartbeat-aware registration paths.
