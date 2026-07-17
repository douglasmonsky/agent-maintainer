# TypeScript Package And Workspace Assessment Boundary

## Status

Accepted.

## Context

Phase 178 adds provenance-rich package-manager and workspace evidence to setup
assessment JSON. The detector reads a fixed set of root metadata, lockfile, and
workspace manifest paths. Keeping that parsing inside the existing repository
evidence module would mix file scanning with package-specific decoding and push
the orchestration module beyond its maintainability limits.

The evidence is advisory. It must not select a package manager, expand workspace
patterns, infer nested ownership, enable a provider, or create an executable
command.

## Decision

Keep package-manager and workspace parsing in
`agent_maintainer.assess.package_workspace_evidence`. The detector depends only
on assessment models and the existing provider-neutral structured-value
normalizer. `agent_maintainer.assess.evidence` owns the single collection edge
to the detector and includes the resulting typed facts in `RepoEvidence`.

Record those dependencies in the package-local Tach contract. Provider,
executor, doctor, catalog, and configuration modules do not depend on the new
detector.

## Consequences

Setup assessment can report deterministic facts and stable advisory issues with
file-and-field provenance while command ownership remains explicit. Package and
workspace decoding stays independently testable, and the general repository
scanner remains focused on bounded evidence orchestration.

The new module is assessment-only. Supporting another declaration shape requires
fixture-backed parsing and an explicit model update; it does not authorize
command inference or provider promotion.

## Alternatives Considered

- Keep all parsing in `assess.evidence`. Rejected because it combines unrelated
  responsibilities and exceeds the module's maintainability budget.
- Put detection in the TypeScript provider. Rejected because setup assessment is
  advisory and must remain independent from provider execution.
- Infer a preferred manager from corroborating signals. Rejected because
  agreement is evidence, not permission to select or execute a tool.

## Verification

Detector and setup-advisor tests cover supported declarations, conflicts,
malformed inputs, literal workspace patterns, provenance, and nested-package
non-inference. Strict Pyright, Pylint, Wemake, exact Tach validation, DocSync,
Markdown lint, the full verifier, and hosted CI enforce the boundary.
