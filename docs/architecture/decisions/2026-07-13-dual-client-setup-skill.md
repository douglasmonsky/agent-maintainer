# 2026-07-13: Dual-Client Setup Skill

## Status

Accepted.

## Context

New repositories benefit from an explicit Agent Maintainer setup offer before
their initial commit. Codex and Claude Code both support personal skills, but a
client-specific implementation would let their onboarding behavior drift.

## Decision

Ship one portable `agent-maintainer-setup` skill in the Python distribution and
install the same bytes into the personal skill directories for Codex and Claude
Code. An ownership manifest records the exact managed files and their hashes.
Updates and uninstall operations stop when those files were edited or the
manifest cannot prove ownership.

The `agent_maintainer.skill` domain owns resource loading and the personal-skill
lifecycle. Its CLI may depend on that lifecycle; lifecycle may depend only on
the resource and model modules. The root CLI exposes this as an undecorated
`skill` command so personal state can be managed outside a Git repository.

The skill teaches the agent to offer Recommended, Guided, or Full control setup
after the new repository's stack is known and before the initial commit. The
skill invokes existing public Agent Maintainer setup commands. It does not
change hook lifecycle internals and does not add an MCP server.

## Consequences

Both clients receive one canonical interaction contract. Package releases can
update stale owned copies safely, while local edits fail closed. Personal client
state stays separate from repository configuration and hook ownership.

## Alternatives Considered

- Maintain separate Codex and Claude Code skills. Rejected because duplicated
  prose and behavior would drift.
- Add an MCP server for setup. Rejected because the existing CLI is sufficient
  for bounded local configuration and has a simpler trust boundary.
- Extend the agent-client hook manager. Rejected because personal skill files
  and per-repository hooks have different ownership and preflight requirements.

## Verification

Lifecycle tests cover install, status, stale updates, local modifications,
rollback, and lossless uninstall for both clients. CLI tests cover repeatable
client selection, parser failures, stable state output, and use outside Git.
Tach and Archguard enforce the recorded domain edges.
