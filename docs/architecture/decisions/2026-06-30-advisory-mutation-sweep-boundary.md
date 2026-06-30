# ADR: Advisory Mutation Sweep Boundary

## Status

Accepted.

## Context

Phase 57 adds `test-intel mutation-sweep`, an advisory planner for deliberate
Mutmut target expansion. The command needs CLI parsing, changed-file discovery,
config loading, sweep ranking, and text/JSON rendering.

The existing `agent_maintainer.test_intel.cli` module already coordinates
several test-intelligence commands and is near style/import thresholds. Placing
all sweep parser and runner logic directly in that module would increase CLI
coupling and make the Tach boundary less useful.

## Decision

Add explicit Tach modules for:

- `mutation.sweep`: pure planning/ranking domain logic.
- `mutation.sweep_reporting`: text and JSON rendering.
- `mutation.sweep_cli`: command-line adapter that loads config, reads changed
  paths, and delegates to the domain/reporting modules.

The top-level `test_intel.cli` module depends on `mutation.cli`, which delegates
to `mutation.sweep_cli` for sweep-specific command handling.

## Consequences

This keeps the main CLI dispatcher small while making the sweep command
independently testable. `mutation.sweep` remains free of CLI config-loading and
stdout/stderr behavior. `mutation.sweep_cli` is allowed to depend on loader and
changed-path helpers because it is an adapter.

Future mutation sweep execution work should keep long-running Mutmut orchestration
outside `mutation.sweep` unless the planner grows into a separate runner domain.
