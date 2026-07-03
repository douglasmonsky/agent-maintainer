# Core Tooling Capability Boundary

## Status

Accepted.

## Context

`agent_maintainer.core` carried tool capability modeling directly beside
execution, reporting, runtime, guidance, and scaffold orchestration. The folder
crossed the structure-cohesion warning threshold even though one clear
responsibility cluster was already visible: capability types, the static
capability registry, and capability evaluation helpers.

## Decision

Move tool capability modeling into `agent_maintainer.core.tooling`:

- `core.tooling.capability_types`
- `core.tooling.capability_registry`
- `core.tooling.capabilities`

Keep executor and doctor setup as callers of this package. Keep the behavior,
check names, doctor messages, and verifier output unchanged.

## Why This Is Not Architecture Drift

The split narrows `core` rather than broadening dependencies. Tool capability
modeling remains inside the core package because it supports setup and execution
across providers, but it now has an explicit subpackage boundary instead of
being mixed with execution/reporting modules.

The Tach contract now models this cluster directly. No dependency was relaxed,
ignored, or synchronized automatically.

## Alternatives Considered

- Leave the files in `core`. Rejected because the cohesion warning identified a
  real cluster and future provider/tool capability work would keep growing the
  root package.
- Move capability helpers under `doctor`. Rejected because verifier execution
  also uses capability-aware missing executable messages.
- Move capability helpers under provider metadata. Rejected because capability
  evaluation is shared by core doctor/setup behavior and all providers.

## Remains Forbidden

- Provider-specific checks should not import doctor orchestration.
- Tool capability helpers should not become a generic package manager installer.
- Tach ignores or broad root buckets should not be used to hide unassigned
  files.
