# Onboarding Policy Presets

## Status

Accepted.

## Context

Phase 30 adds deterministic onboarding presets for `agent-maintainer init`.
The initializer already owns starter file selection, while the starter
configuration template owns generated `[tool.agent_maintainer]` policy.

## Decision

Add `agent_maintainer.core.scaffold.presets` as a core scaffolding module and
assign it explicitly in the local Tach domain contract.

The module contains preset policy values and deterministic template overlay
logic. `init --track` remains responsible for which files are written.
`init --preset` only tunes the starter config content.

## Alternatives Considered

- Put preset logic directly in `initializer`: rejected because argument parsing
  and file writing would mix with policy-value definitions.
- Generate separate template files per preset: rejected because it would create
  high-drift copies of the same starter config.
- Make presets imply tracks: rejected because file-set selection and policy
  strictness should stay independently composable.

## Boundaries

Presets do not inspect repositories, run checks, or infer project type. They are
named deterministic starter policies. Users can still edit the generated config
after initialization.
