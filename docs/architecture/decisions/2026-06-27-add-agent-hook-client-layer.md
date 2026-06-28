# Add Agent Hook Client Layer

## Context

Agent Maintainer already shipped Codex hook wrappers under `.codex/hooks`.
Adding Claude Code support should not create a second, divergent verifier path.
Both clients need the same fast post-edit checks, stop-time verification, bytecode
write policy, and hook audit trail.

## Decision

Add a package-owned `agent_maintainer.hooks` layer and make repo-local Codex and
Claude Code hook files thin wrappers around that shared runtime.

`tach.toml` now treats `.claude/hooks` as a source root alongside `.codex/hooks`.
Each generated wrapper is explicitly assigned to the entrypoint layer. The
package-owned hook CLI, manager, templates, audit writer, and runtime are
assigned to the existing entrypoint, orchestration, and runtime layers.

## Rationale

This keeps client-specific setup in adapters and keeps maintenance behavior in
one runtime. Codex and Claude Code can differ in config file format and hook
event names without forking verification, audit, or subprocess handling.

## Alternatives Considered

- Keep Claude Code hooks as independent scripts. That would duplicate Codex
  behavior and make future fixes drift-prone.
- Leave `.claude/hooks` outside Tach. That would make hook wrappers invisible to
  the architecture contract even though they block agent workflows.
- Use user-global hooks only. That would reduce repository transparency and make
  public onboarding less reviewable.

## Still Forbidden

Hook wrappers should remain thin entrypoints. They should not grow verifier
logic, parse project config, mutate source files, or bypass the shared runtime.
