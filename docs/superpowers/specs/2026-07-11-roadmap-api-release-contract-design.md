# Roadmap, API Support, and Beta Qualification Design

**Date:** 2026-07-11

**Status:** Approved direction, written contract

**Scope:** Roadmap truth, pre-1.0 API policy, compatibility inventory, extracted-package ownership, and non-publishing `0.1.0b6` qualification

## Problem

The active roadmap still describes a 1,265-diagnostic strict-Pyright backlog even
though the repository is strict and clean. It also leaves the support status of
distributed import paths and compatibility shims implicit. That makes the next
release harder to qualify and gives maintainers and coding agents stale recovery
instructions.

## Goals

- Make `docs/ROADMAP.md` describe current repository state and distinguish
  completed work from genuinely open release work.
- Publish a pre-1.0 support policy for documented commands, machine-readable
  formats, configuration, and Python imports.
- Inventory compatibility shims with an owner, support window, removal
  condition, and earliest removal release.
- Add `agent_waits` to the extracted-package ownership narrative and the
  secondary import-direction regression test.
- Qualify one exact `0.1.0b6` candidate commit without tagging, publishing, or
  claiming external release completion.

## Non-goals

- Removing compatibility shims before the beta candidate ships.
- Treating every distributed top-level package as a supported public API.
- Refactoring the 130-field `MaintainerConfig` before `0.1.0b6`.
- Publishing to TestPyPI or PyPI, creating a tag or GitHub release, or changing
  production credentials and release environments.
- Running the Phase 176 real Codex-turn smoke. That remains separately gated
  because it creates an actual external turn.

## Chosen approach

### Roadmap truth

Replace the stale strict-typing section with a completed strict-cutover record.
Keep the following items open until their implementation lands: help and public
documentation classification, attention priority/provenance, wait-lifecycle
convergence, and `0.1.0b6` exact-commit qualification. Mark schema validation as
complete because the ledger reader already enforces schema version, file count,
normalized repository paths, duplicate rejection, and finite unit-interval
scores.

The roadmap remains an active tracker, not a historical changelog. Detailed
implementation history belongs in the existing archive and change-plan files.

### Pre-1.0 support policy

Add one public policy document with three explicit tiers:

1. **Current-version documented surfaces:** the `agent-maintainer`, `archguard`,
   and `docsync` console entry points; documented `[tool.agent_maintainer]`
   configuration; and documented schema-versioned formats are expected to work
   for the exact installed beta version. They carry no cross-version
   compatibility promise before 1.0.
2. **Current Python entry points:** `docsync.api` remains the intended DocSync
   integration boundary for current code, but its signature may change between
   beta releases without a deprecation window.
3. **Internal/unstable surfaces:** implementation modules under
   `agent_maintainer`, `archguard`, and the extracted top-level packages unless
   explicitly promoted. Distribution in the wheel is not, by itself, a support
   promise.

During `0.x`, commands, configuration, formats, and imports may change or be
removed without a compatibility shim or deprecation release. Release notes and
upgrade guidance should explain material user-facing changes when useful, but
they are communication rather than a compatibility gate.

### Compatibility inventory

Create a checked-in cleanup inventory grouped by boundary rather than pretending
each thin forwarding module is an independent product. Every group records:

- owning package and replacement import;
- all forwarding modules in the group;
- current internal callers, docs, or tests that must migrate with removal; and
- the deletion rule: migrate current callers and delete the shim in the same
  tested change.

Compatibility is not a reason to retain a shim. This track does not mass-delete
forwarders blindly because an active internal caller would break, but no grace
release, notice period, or external import promise blocks deletion.

### `agent_waits` ownership

Document `agent_waits` as the reusable, product-neutral wait-state package. Add
it to `tests/architecture/test_internal_package_boundaries.py` with forbidden
imports from product packages such as `agent_maintainer`, `archguard`, and
`docsync`. Tach remains the primary architecture contract; the AST test remains
a small, readable secondary regression.

### Exact-commit beta qualification

After all architecture-hardening chunks are merged, select the resulting
`main` SHA and run the complete local candidate matrix:

- `just doctor`
- `just verify-precommit`
- `just verify`
- `just verify-ci`
- `just verify-security`
- `just verify-manual`
- `just release-check`

Record the exact SHA, manifests, artifact smoke result, supported-Python
coverage, and any skipped externally gated step in
`docs/releases/0.1.0b6.md`. The release index continues to call b6 an
unpublished candidate. Publication is a later, explicitly authorized action.
Because a Git commit cannot contain its own SHA, this record is an
evidence-only follow-up commit that names the unchanged qualified candidate
SHA; it does not redefine the follow-up documentation commit as the candidate.

## Alternatives considered

- **Leave beta instability implicit.** Rejected because users and agents need
  to know that current documentation is not a cross-version promise.
- **Freeze every import present in the wheel.** Rejected because packaging
  implementation units are not all intended libraries and a blanket promise
  would prevent needed beta refactoring.
- **Delete every shim without migrating active callers.** Rejected because beta
  freedom permits breaking external compatibility, not knowingly breaking the
  repository's current runtime and test graph.

## Error handling and evidence

- A stale or unclassified shim blocks completion of the inventory task.
- A failed qualification command blocks an exact-commit qualification claim;
  its repair capsule is handled before rerunning the affected profile.
- Candidate notes must say `not run` or `not authorized` for gated work rather
  than silently omitting it.
- No generated distribution artifact is committed.

## Acceptance criteria

- The active roadmap contains no stale strict-Pyright diagnostic target.
- The support policy makes CLI, format, configuration, and import commitments
  distinguishable at a glance.
- Every known shim group has a canonical replacement and immediate tested
  deletion rule, with no support window or earliest-release gate.
- `agent_waits` has documented ownership and a passing secondary dependency
  regression.
- One exact b6 candidate SHA has complete local qualification evidence, with
  publication and the real-turn smoke still truthfully marked pending.
