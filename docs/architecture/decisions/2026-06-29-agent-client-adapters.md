# Agent Client Adapters

## Status

Accepted.

## Context

Phase 33 separates client-specific hook behavior from the generic hook manager.
Codex and Claude Code currently share install, status, and template merging
workflow, but their config files and hook paths are different.

## Decision

Add `agent_maintainer.hooks.adapters` with an `AgentClientAdapter` protocol and
two implementations: Codex and Claude Code. Keep the existing hook manager as
the orchestrator for confirmation, dry-run, backup, merge, and file writes.
Adapters own client names, config paths, hook paths, planned writes, status, and
future uninstall path discovery.

## Alternatives Considered

- Keep client branching in `hooks.manager`: rejected because adding more
  managed clients would continue growing conditional path logic.
- Add adapters for every possible agent client now: rejected because Phase 33
  explicitly limits implementation to Codex and Claude Code.
- Move file writing into adapters: rejected because backup, dry-run, and merge
  behavior should remain one generic hook-manager policy.

## Boundaries

Adapters may describe and plan client-specific files, but they must not write to
disk. The hook manager remains responsible for user permission prompts, backups,
merges, and writes.
