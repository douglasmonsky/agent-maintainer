# Architecture Decision: Context Expansion Commands

Status: accepted

## Context

Phase 9 adds safe expansion commands for verifier failures and logs. These
commands read `.verify-logs/manifest.json` and individual check logs, then
return bounded text or structured JSON. The existing `agent_maintainer.context`
package already owns bounded context primitives, but the new modules perform
filesystem reads and command rendering.

## Decision

Add `agent_maintainer.context.cli` to the orchestration layer because it owns
argument parsing and subcommand dispatch.

Add `agent_maintainer.context.failures` and `agent_maintainer.context.logs` to
the runtime layer because they read local diagnostic artifacts and produce
bounded expansion output. They may depend on context budget primitives and
manifest constants, but they must not run verification or decide check results.

## Alternatives Considered

Putting the expansion logic under `verify` was rejected because these commands
are post-run diagnostic readers, not verification execution.

Putting the modules in the shared layer was rejected because filesystem reads
are runtime behavior, while the shared context layer should stay focused on
portable bounded-output primitives.

## Still Forbidden

Context expansion commands must not dump unbounded logs by default. Large
expansions require explicit budget increases or `--confirm-large`.
