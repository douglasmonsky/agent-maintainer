# Agent Waits Core Boundary

## Status

Accepted.

## Context

Background PR waits introduced durable wait records, compact resume capsules, and
Codex heartbeat prompts under `agent_maintainer.wait`. Those concepts are useful
outside Agent Maintainer-specific GitHub PR polling and can become a standalone
agent workflow primitive.

## Decision

Add top-level package `agent_waits` reusable wait orchestration primitives:

- wait result capsules;
- wait status/result constants;
- heartbeat metadata defaults for repo-scoped wait notification;
- durable generic wait records atomic registry writes;
- wait record rendering;
- Codex-safe foreground-wait guards, background registration rendering, and
  heartbeat prompt text.

Keep `agent_maintainer.wait` layer maintainer-specific wait kinds, including
GitHub PR completion semantics, verifier waits, GitHub run waits, CLI commands,
and detached watcher process wiring.

## Boundary

`agent_waits` must not import `agent_maintainer`. It may own generic records,
repo heartbeat metadata policy, rendering, and Codex environment policy.
`agent_maintainer.wait` may depend on `agent_waits` to add external-system
polling and terminal-result mapping. Within `agent_waits`, `constants`,
`heartbeat`, `models`, `registry`, and `rendering` stay adapter-free
leaf/domain modules; `broker` depends on registry and models for rendering
only.

## Alternatives Considered

- Leave all wait primitives under `agent_maintainer.wait`. Rejected because the
  broker and registry are growing beyond one package's application boundary.
- Extract a separate installable distribution immediately. Rejected because the
  package needs more than one internal consumer before package metadata and
  release workflow churn are worth it.
- Move GitHub PR polling into `agent_waits`. Rejected because that would make the
  reusable package depend on Agent Maintainer's current application behavior.

## Consequences

The repo has a clearer growth path for background waits across tool use without
premature standalone packaging. Future wait kinds should add generic record
support in `agent_waits` only when the behavior is not tied to Agent Maintainer
commands or external adapters.
