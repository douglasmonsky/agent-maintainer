# 2026-07-09: Derived Artifact Read Safety

## Status

Accepted.

## Context

Runtime-event summaries and attention scoring consume repository-generated
JSONL, ledgers, verifier manifests, DocSync evidence, and file-baseline reports.
Those inputs may be selected indirectly through MCP arguments or artifact
manifests. The original readers followed symlinks, accepted special and
non-UTF-8 files, truncated oversized inputs after opening them, and allowed
absolute artifact directories outside the repository.

## Decision

Reuse `agent_context.reading.file_safety` at every derived-artifact content
boundary. `agent_maintainer.runtime_events.read` accepts only bounded regular
UTF-8 JSONL leaves, rejects unsafe event directories before enumeration, uses
no-follow metadata for ordering, and caps default aggregate reads at the newest
32 files. `agent_maintainer.attention.builder` requires an explicit workspace
root when loading a ledger. `agent_maintainer.attention.signal_artifacts`
confines manifest, DocSync, and baseline inputs to the repository and rejects
symlinked run directories before manifest discovery; `attention.signals`
orchestrates those bounded readers and confined runtime events. Runtime-event
and verifier-manifest aggregation both read at most the deterministic newest 32
files by default.

The exact new architecture edges are:

- `agent_maintainer.runtime_events.read` to
  `agent_context.reading.file_safety`;
- `agent_maintainer.attention.builder` to
  `agent_context.reading.file_safety`; and
- `agent_maintainer.attention.signal_artifacts` to
  `agent_context.reading.file_safety` and
  `agent_maintainer.runtime_events.read`; and
- `agent_maintainer.attention.signals` to
  `agent_maintainer.attention.signal_artifacts`.

These are inward dependencies on a reusable safety policy, not imports of MCP,
CLI, verifier, or attention orchestration internals.

## Alternatives Considered

- Duplicate the file checks in each package. Rejected because the policies
  would drift and descriptor-level no-follow checks are easy to implement
  inconsistently.
- Truncate an artifact after opening it. Rejected because that still opens
  FIFOs and other special files and treats incomplete JSON as evidence.
- Trust artifact directories because the files are locally generated. Rejected
  because repository contents and MCP-derived relative paths are untrusted
  inputs at read time.

## Boundary Rules

- Derived artifact content reads remain bounded, UTF-8, and regular-file only.
- Repository-aware attention reads require an explicit canonical workspace
  root and refuse paths outside it.
- Runtime-event ordering never calls following `stat` on an untrusted leaf.
- Verifier run-directory discovery does not follow symlinks.
- Runtime-event and attention packages remain independent of MCP and verifier
  implementation modules.

## Verification

Focused tests cover outside canaries, symlinked leaves and parents, FIFOs,
sparse oversized files, non-UTF-8 inputs, aggregate file caps, and legitimate
repository-relative artifacts. Ruff, Pyright, and Tach verify the affected
modules and exact dependency declarations.

## Residual Risk

Directory validation and later enumeration are separate operations. A hostile
local process with concurrent repository write access could race directory
replacement. If mutually hostile local processes enter the threat model, move
directory traversal to an `openat`-style descriptor walk or an operating-system
sandbox.
