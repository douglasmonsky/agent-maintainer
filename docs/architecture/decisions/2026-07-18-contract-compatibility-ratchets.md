# Contract Compatibility Ratchet Boundary

## Status

Accepted.

## Context

Phase 184 needs to compare repository-owned configuration, CLI, Python API, and
JSON Schema contracts without importing target code, running target commands,
or trusting a rewritten baseline. The policy and generated evidence cross a
security-sensitive filesystem boundary, while later extraction and comparison
logic needs one stable inward-facing domain model.

Keeping these responsibilities in root orchestration would mix strict input
validation, semantic normalization, Git history, reporting, and command
routing. Keeping baseline or policy parsing in the extractor adapters would
duplicate confinement and fingerprint rules and make compatibility evidence
depend on the selected adapter.

## Decision

Add `agent_maintainer.contracts` as an inward-facing domain. Its immutable
models and resource limits have no outward dependencies. Repository-confined
path handling may depend on the shared `agent_maintainer.core.repo_paths`
primitive; strict policy and canonical baseline modules may depend only on
that path boundary and sibling contract modules.

Policy remains authored, strict, versioned TOML. Baselines remain generated,
canonical JSON with document and descriptor fingerprints. Reads accept only
bounded UTF-8 regular files whose identity is stable across `lstat` and open;
writes use a mode-`0o600` temporary regular file, `fsync`, parent confinement
revalidation, and exact atomic replacement. Symlinks, special files, unsafe
paths, unknown keys, duplicate identities, and tampered fingerprints fail
closed.

Future extractors, comparison, versioning, Git-base loading, reporting, and
service orchestration stay inside this domain with explicit Tach dependencies.
Adapters receive repository text or structured facts and do not import runtime
application objects, execute target commands, use a shell, or access a network.
Root CLI and catalog integration may depend inward on the completed service;
the contracts domain must not depend back on those outward adapters.

Historical loading resolves an authored base ref to one commit before any blob
read, verifies both contract paths are regular Git tree blobs, and then reads
bounded UTF-8 content only through that resolved identity. Service orchestration
proves current baseline freshness before comparing base descriptors with live
descriptors, reads structured Git path facts once, and evaluates revision,
package-version, and migration obligations independently.

Extractor routing depends on concrete adapters, while adapters depend on a
separate inward-only normalization module for bounded JSON, canonical ordering,
and descriptor construction. Adapters do not depend back on routing. This keeps
the dependency graph acyclic while preserving one public extraction entry point
and one shared fingerprint implementation.

Python API extraction is AST-only. It accepts static `__all__` or explicit
policy nominations, records signature shape and default presence without
evaluating defaults, renders only a strict annotation-node allowlist, and
retains only bounded JSON literal constants. Module bodies, decorators, imports,
and target runtime objects are never executed or used for discovery.

JSON Schema extraction retains only the bounded structural subset needed for
compatibility checks. It resolves local `#/$defs/<escaped-name>` references,
rejects remote or file references and malformed or cyclic graphs, and records
exact JSON Pointer paths for known composition keywords whose semantics are not
proved. Those paths remain review-required evidence rather than being guessed
into merged schemas.

Comparison operates only on normalized descriptors. Identity-bearing arrays
and schema property maps become deterministic member operations, while changed
semantic leaves use a small shared operation vocabulary and kind-aware
classifiers. A review decision is applied only after the original change
fingerprint is computed, and it can resolve only that exact review-required
finding; it cannot weaken compatibility that the classifier already proved.

Revision, package-version, and migration requirements are evaluated as
independent obligations. Revision checks compare authored contract identities;
package recommendations use the declared PEP 440 parser and repository-owned
stable/beta impact policy; migration checks consume structured Git facts through
a read-only protocol and count only added, modified, or renamed destination
paths. Segment-aware matching stays inside the contracts domain so it does not
depend outward on verifier orchestration or Git execution.

## Consequences

Every contract operation uses one repository-confinement and canonical
fingerprint boundary. A changed baseline cannot conceal semantic drift because
later enforcement compares base, current, and live descriptors independently.
The strict Tach domain file makes each new dependency edge reviewable and
prevents orchestration concerns from leaking into models or storage code.

The domain adds deliberate validation code and generated evidence that must be
kept byte-stable. New contract kinds require an explicit extractor, bounded
normalization rules, compatibility tests, and a reviewed Tach edge rather than
runtime reflection or permissive fallback.

## Alternatives Considered

- Put compatibility checks directly in the verifier catalog. Rejected because
  catalog entries should route checks, not own semantic policy or storage.
- Let each extractor read policy and baselines. Rejected because confinement,
  canonicalization, and anti-tamper behavior would diverge across adapters.
- Import target packages or run their CLIs to discover contracts. Rejected
  because it executes untrusted repository behavior and makes evidence
  environment-dependent.
- Treat the generated baseline as authoritative current state. Rejected because
  a baseline rewrite could otherwise hide a breaking live contract change.

## Verification

Focused tests cover strict policy rejection, canonical fingerprints, duplicate
and unsafe source rejection, bounded UTF-8 regular-file reads, FIFO and symlink
rejection, stable file identity, atomic replacement, and preservation of the
old baseline when replacement fails. Ruff, strict Pyright, exact Tach,
change-plan validation, the diff-aware verification planner, and the repository
verifier enforce the boundary.
