# 2026-07-05: MCP Surface Boundary

## Status

Accepted.

## Context

Phase 156 adds an optional MCP surface for the highest-return Agent Maintainer
commands. The CLI remains the primary product interface, and core installs must
not require MCP dependencies.

## Decision

Add `agent_maintainer.mcp` as an adapter package over existing command
contracts. MCP tools build bounded command requests for verifier, context,
runtime events, attention, and DocSync workflows. The optional server imports
the MCP SDK only when `mcp serve` starts.

The MCP package must not own verifier semantics, context-pack construction,
DocSync policy, attention scoring, or orchestration policy. It only translates
typed tool requests into existing Agent Maintainer or DocSync command calls and
returns bounded results.

## Boundary Rules

- `agent_maintainer.mcp.models` owns MCP-facing request/result models.
- `agent_maintainer.mcp.tools` owns command request construction and bounded
  subprocess execution.
- `agent_maintainer.mcp.server` owns optional FastMCP registration.
- Core verifier, context, attention, DocSync, and runtime-event packages remain
  authoritative for their behavior.
- Optional MCP dependencies stay outside the core extra.

## Alternatives Considered

- Register MCP tools directly in the top-level CLI. Rejected because it would
  blur optional adapter code with the canonical command router.
- Import the MCP SDK at package import time. Rejected because core installs
  should keep working without MCP dependencies.
- Reimplement domain logic inside MCP tools. Rejected because it would create a
  second behavior path.

## Verification

Tach owns this boundary through `src/agent_maintainer/mcp/tach.domain.toml`.
Tests cover request construction, bounded output, missing dependency guidance,
and server tool registration.
