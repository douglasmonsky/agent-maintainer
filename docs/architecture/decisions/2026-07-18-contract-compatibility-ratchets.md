# Contract Compatibility Ratchet Boundary

## Status

Accepted.

## Context

Phase 184 needs to compare repository-owned configuration, CLI, Python API, and
JSON Schema contracts without importing target code, running target commands,
or trusting a rewritten baseline. The policy and generated evidence cross a
security-sensitive filesystem boundary, while later extraction and comparison
logic needs one stable inward-facing domain model.

Agent Maintainer remains pre-1.0. The boundary must prevent accidental drift
without freezing every beta surface or claiming compatibility across installed
versions.

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
Staged verification uses a separate index-state boundary: bounded Git readers
accept only one regular stage-zero blob per declared path, and a controlled
temporary root materializes only policy, baseline, package version, and contract
sources. The service keeps historical Git access rooted in the real repository
and uses the cached diff for migration evidence. Tach records the new
`index_state`, shared validation, and Git path dependencies explicitly.
Enforcement and advisory checks reject stale current evidence before historical
comparison. Snapshot mode alone treats that staleness as the prospective write,
but still compares base descriptors directly with live extraction and permits
the atomic replacement only after every independent obligation is satisfied.

Root command integration remains a lazy target-aware adapter. The verifier
catalog describes the public `contract check` subprocess without importing the
contracts domain, skips it only when authored policy is absent, and assigns it
to the static-policy group. The executor validates the command's complete JSON
stdout before retaining it as a run artifact, so configuration diagnostics
cannot masquerade as a structured contract report.

The public workflow is explicit: `contract diff` is advisory, `contract check`
enforces independent obligations, and `contract snapshot --write` updates only
canonical evidence after those obligations pass. Agent Maintainer dogfoods
configuration capabilities, its CLI manifest, `docsync.api`, Codex app-server
wait messages, and durable `agent_waits` records.

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
- Compare raw source hashes or golden text. Rejected because formatting and
  implementation changes are not semantic contract changes.
- Maintain independent surface-specific ratchets. Rejected because policy,
  version rules, decisions, repair facts, and enforcement would diverge.
- Freeze all beta surfaces. Rejected because that contradicts the explicit
  pre-1.0 support policy and prevents necessary evolution.
- Accept baselines or edit versions automatically. Rejected because the
  control would become its own bypass and hide the review decision.

## Forbidden Behavior

The ratchet must not import arbitrary target modules, execute target commands,
evaluate a shell, use the network, infer unsupported schema semantics, rewrite
versions or migrations, accept a baseline implicitly, suppress other checks, or
claim historical compatibility when evidence is unavailable.

## Qualification Boundaries

Qualification keeps the classifier dispatcher separate from member-specific
rules, Git path parsing separate from Git process and historical-state access,
and atomic baseline writes separate from canonical baseline parsing and
rendering. Shared validation owns explicit input errors, while command
environment construction remains outside the executor. Tach declares these
dependencies directly so the smaller modules remain enforced architectural
boundaries rather than quality-tool exceptions.

## Verification

Focused tests cover strict policy rejection, canonical fingerprints, duplicate
and unsafe source rejection, bounded UTF-8 regular-file reads, FIFO and symlink
rejection, stable file identity, atomic replacement, and preservation of the
old baseline when replacement fails. Ruff, strict Pyright, exact Tach,
change-plan validation, the diff-aware verification planner, and the repository
verifier enforce the boundary. Exact classifier mutation qualification, the
five dogfood freshness checks, DocSync, full, CI-equivalent, security, review,
and protected hosted gates complete Phase 184.
