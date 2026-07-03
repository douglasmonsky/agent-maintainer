# Architecture Decision: DocSync Release And Architecture Trace

Status: accepted

## What Changed?

Add DocSync evidence markers for release publishing discipline and architecture
policy documentation. The Tach policy file change is limited to trace comments
around the existing strict source-root and `root_module = "forbid"` contract.

## Why Necessary?

Release and architecture policy docs are high-trust maintainer documents. They
should be tied to current workflow, release-test, Tach, and Archguard evidence
instead of drifting as standalone prose.

## Why This Not Just Architecture Drift?

The architecture contract is unchanged. Source roots, strict root-module
handling, module ownership, and dependency boundaries remain identical. The
change only lets DocSync verify that public architecture guidance points at the
actual Tach and Archguard enforcement surfaces.

## Alternatives Considered

1. Leave release and architecture docs outside DocSync for now. Rejected because
   these docs define trust-critical behavior and should be part of the dogfood
   ratchet.
2. Avoid touching `tach.toml` by using inferred evidence. Rejected because this
   repository requires explicit evidence regions for DocSync traceability.
3. Treat trace comments as exempt from architecture decision notes. Rejected
   because the gate should stay mechanically simple and conservative.

## Boundary Impact

DocSync gains evidence coverage for release and architecture documentation.
Tach policy, Archguard behavior, and package boundaries are unchanged.

## What Remains Forbidden?

Do not add broad Tach modules, relax `root_module = "forbid"`, run `tach sync`
as a silent fix, or weaken architecture decision-note enforcement to make trace
work easier.

## Review Or Expiration Condition

Revisit if DocSync grows a dedicated architecture-policy evidence adapter that
can prove comment-only trace changes without touching Tach policy files.
