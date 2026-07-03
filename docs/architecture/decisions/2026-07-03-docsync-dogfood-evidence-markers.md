# Architecture Decision: DocSync Dogfood Evidence Markers

Status: accepted

## What Changed?

DocSync's own Tach domain file now contains a DocSync evidence marker around
the existing extractability contract. The dependency graph and allowed module
relationships did not change.

## Why Necessary?

The repository is beginning to dogfood DocSync. Its first trace needs live
evidence for the durable claim that `docsync` remains extractable and does not
depend on `agent_maintainer` or `archguard`.

## Why This Is Not Architecture Drift

The marker is a TOML comment only. It does not add, remove, or relax any Tach
module dependency. `src/docsync/tach.domain.toml` still keeps DocSync
independent from Agent Maintainer and Archguard.

## Alternatives Considered

1. Evidence the claim only through prose. Rejected because DocSync should link
   durable documentation claims to source-controlled checks or policy files.
2. Skip the Tach-domain evidence marker. Rejected because the Tach file is the
   clearest source of truth for the package boundary.
3. Relax the architecture-decision requirement for comment-only policy edits.
   Rejected because the repo intentionally treats architecture policy files as
   high-signal change points.

## Follow-Up

When DocSync coverage expands beyond this seed, add evidence only for durable
claims that materially benefit from traceability. Do not turn DocSync evidence
markers into broad documentation noise.
