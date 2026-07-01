# Verify Artifact Manifest Boundary

## Status

Accepted.

## Context

`agent_maintainer.verify.artifacts` writes run-scoped verifier artifacts,
latest pointers, manifests, failure notes, history, and PR summaries. The file
was near the reviewability warning zone and mixed file-writing orchestration
with manifest check payload formatting.

## Decision

Move manifest check payload helpers into
`agent_maintainer.verify.artifact_manifest`. Keep `artifacts.py` responsible for
writing files, run snapshots, and latest pointers. The new module receives plain
`repo_root` and `MaintainerConfig` values rather than importing `RunContext`, so
the boundary does not create a cycle.

Update the verify Tach domain contract so `artifacts` may depend on
`artifact_manifest`, and `artifact_manifest` depends only on config, context
budget/model, and check result models.

## Alternatives Considered

- Move last-failure rendering first. That would require a context protocol or a
  larger context model extraction.
- Move `RunContext` to a separate model module. That may be useful later, but it
  was broader than needed for this cleanup.

## Consequences

Manifest serialization is isolated and easier to test. `artifacts.py` is shorter
and remains focused on artifact lifecycle responsibilities.
