# Context Package Boundary Split

## Status

Accepted.

## Context

The context package grew into a flat folder with readers, pack assembly,
compression backends, and exact repair fact extraction all beside one another.
That made the Tach contract harder to review and triggered structure-cohesion
pressure without improving maintainability.

The repository still requires `root_module = "forbid"` in Tach. Splitting the
folder must keep every source file assigned to an explicit module instead of
using broad root buckets.

## Decision

Split `agent_maintainer.context` into responsibility-focused subpackages:

- `agent_maintainer.context.reading` owns safe file, log, and diff readers.
- `agent_maintainer.context.pack` owns context pack assembly, rendering,
  sanitizing, compression orchestration, and exact repair fact extraction.
- `agent_maintainer.context.compression` owns compression contracts, built-in
  backends, and optional Headroom adapter code.

Keep `agent_maintainer.context.cli` as the orchestration entrypoint that may
depend on the subpackages. Keep shared budget, formatting, failure, and model
modules at the context package root where they remain stable primitives.

## Consequences

The direct Python file count in `agent_maintainer.context` drops below the
folder-count warning threshold, and the Tach domain contract now makes the
allowed direction explicit. `reading` modules do not depend on pack or
compression modules. `pack` modules may compose reading helpers and ratchet
state. `compression` modules remain isolated from file and diff readers.

## Alternatives Considered

Leaving the flat package in place was rejected because it encouraged future
agents to add one more sibling module instead of choosing an ownership boundary.

Adding Tach ignores or relaxing `root_module = "forbid"` was rejected because
that would hide the architecture drift instead of fixing it.

Creating compatibility shim modules in the old flat locations was rejected
because there are no external adopters for these internal modules and shims
would preserve the same flat-folder pressure.

## Still Forbidden

Reader modules must not import context pack builders, compression backends, hook
runtime modules, CLI modules, or verifier orchestration. Compression provider
adapters must receive sanitized supporting context only. Pack generation may
compose lower-level helpers but must not own scanner policy or hook execution.
