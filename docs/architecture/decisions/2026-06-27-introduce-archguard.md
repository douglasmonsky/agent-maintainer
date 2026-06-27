# Architecture Decision: Introduce Archguard

Status: accepted

## What Changed?

A new top-level `archguard` package was added under `src/`. Agent Maintainer
now consumes Archguard for Tach configuration validation and architecture
decision-note enforcement.

## Why Was This Necessary?

Agent Maintainer already enforces Tach architecture boundaries, but Tach
configuration itself can drift if agents or maintainers relax `tach.toml`
without explaining the design reason. Archguard owns governance for architecture
policy changes.

## Why Is This Not Just Architecture Drift?

This change makes architecture policy stricter. It does not relax a module
dependency, add an unchecked Tach module, or bypass a boundary. It introduces a
gate requiring design documentation when architecture policy files change.

## Alternatives Considered

1. Keep the Tach helper inside `agent_maintainer`.
2. Create a separate repository immediately.
3. Fork Tach.

The chosen approach keeps implementation local while creating a clean package
boundary that can be extracted later.

## Boundary Impact

`archguard` owns architecture policy governance. `agent_maintainer` remains the
orchestration layer that runs checks across profiles. Tach remains the
import-boundary enforcement backend.

## What Remains Forbidden?

Agents should not weaken `tach.toml`, add Tach ignores, add broad dependencies,
or move modules to unchecked status without a decision note.

## Review Or Expiration Condition

Revisit this decision once Archguard has multiple checks or downstream users. At
that point, decide whether to publish it as a separate distribution.
