# Architecture Decision: Test Intelligence Package

Status: accepted

## Context

Phase 7 adds deterministic guidance for likely tests related to changed source.
The feature needs Git diff discovery, AST import scanning, optional coverage
artifact reads, and report rendering. Because `tach.toml` uses
`root_module = "forbid"`, the new package must be explicitly assigned to
architecture layers.

## Decision

Add `agent_maintainer.test_intel.cli` to the orchestration layer because it owns
CLI argument handling and command assembly.

Add `agent_maintainer.test_intel`, `changed`, `coverage`, `mapping`, and
`reporting` to the runtime layer because they read local repository state,
inspect files, and format deterministic command output. Add
`hypothesis_candidates`, `hypothesis_scaffolds`, `hypothesis_reporting`,
`mutation.targets`, `mutation.results_reporting`, `crosshair_candidates`, and
`crosshair_reporting` to the same runtime layer because they inspect source ASTs
and emit advisory test-improvement guidance without changing verifier outcomes.

Add `agent_maintainer.test_intel.models` to the models layer because it contains
pure report value objects.

## Alternatives Considered

Putting test intelligence under `verify` was rejected because the command is an
agent-facing guidance surface, not a verifier gate.

Putting all modules in orchestration was rejected because mapping and reporting
are reusable runtime behavior with focused unit tests.

## Still Forbidden

Test intelligence must not decide whether verification passes. It may suggest
focused tests and expose evidence, but pytest, coverage, diff-cover, and other
configured gates remain the source of truth for correctness.
