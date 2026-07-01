# Core Scaffolding Package Boundary

## Status

Accepted.

## Context

`agent_maintainer.core` reached the structure-cohesion warning threshold with
initializer orchestration, starter-file templates, starter config text, and
policy presets sitting beside verifier runtime helpers. Those files form one
coherent onboarding/scaffolding concern and were being kept flat only because
they started small.

## Decision

Move the initializer cluster into `agent_maintainer.core.scaffold`:

- `scaffold.initializer` owns the `init` command orchestration.
- `scaffold.templates` owns starter file assembly.
- `scaffold.template_config` owns the starter TOML template.
- `scaffold.presets` owns starter policy preset tuning.

Keep each moved file explicitly assigned in the local Tach domain contract, and
point the root CLI contract at `agent_maintainer.core.scaffold.initializer`.

## Consequences

The `core` package remains focused on runtime orchestration, command execution,
reporting, and shared configuration helpers. Scaffolding can grow without
pushing unrelated core modules past the cohesion warning threshold.

## Alternatives Considered

- Keep the flat layout and accept the warning. Rejected because the file names
  already showed a clear scaffolding cluster.
- Create a top-level `initializer` package. Rejected because these helpers are
  still core CLI support, not a separate product domain.
- Relax the structure-cohesion rule. Rejected because the warning identified a
  real responsibility cluster.

## Still Forbidden

The scaffold package must not become a dumping ground for verifier runtime,
doctor, hook, or assessment behavior. New files should belong there only when
they generate or tune starter repository adoption files.
