# Repair Plan Command

## Status

Accepted.

## Context

Phase 32 adds a read-only `repair-plan` command that turns existing bounded
context, ratchet, test-intelligence, and verifier commands into a repair
sequence agents can follow before editing.

## Decision

Add `agent_maintainer.repair_plan` as a small package. The command-line adapter
belongs to orchestration, the planner and renderer belong to runtime, and the
plan dataclasses belong to models. The command never edits repository files or
updates verifier state; it only prints Markdown or JSON.

## Alternatives Considered

- Put the command in the top-level CLI: rejected because the top-level command
  table should stay thin.
- Put repair planning into context commands: rejected because context commands
  expand bounded facts, while repair plans sequence multiple existing commands.
- Reuse change-plan files: rejected because repair plans are immediate,
  non-mutating guidance and do not create durable change-plan artifacts.

## Boundaries

Repair plans may reference existing Agent Maintainer commands but must not call
them or mutate source, configuration, baselines, or diagnostics. Tach remains
the enforcement layer for module ownership and dependency direction.
