# Ratcheting

This document tracks planned beta work. implementation will land in small
phases. Public behavior must remain deterministic and bounded by default.

Ratcheting is the planned adoption model for repositories with existing
violations. Instead of forcing a legacy repository to become clean all at once,
Agent Maintainer should distinguish new or worsened problems from known
baseline debt.

Planned capabilities include baseline status, ranked repair targets,
changed-code discipline, and generated agent guidance in `AGENTS.ratchet.md`.

The intended outcome is stricter maintenance over time without turning every
old violation into immediate noise for the current change.
