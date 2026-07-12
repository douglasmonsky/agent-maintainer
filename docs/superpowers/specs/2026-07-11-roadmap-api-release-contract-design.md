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

1. **Supported beta surfaces:** the `agent-maintainer`, `archguard`, and
   `docsync` console entry points; documented subcommands and exit behavior;
   documented `[tool.agent_maintainer]` configuration; and documented JSON or
   artifact schemas carrying a schema version.
2. **Intended beta Python API:** only import paths explicitly named in the
   policy or an API document. `docsync.api` is included because it is already
   declared as the stable DocSync API. Adding another import requires a docs
   change and a compatibility test.
3. **Internal/unstable surfaces:** implementation modules under
   `agent_maintainer`, `archguard`, and the extracted top-level packages unless
   explicitly promoted. Distribution in the wheel is not, by itself, a support
   promise.

During `0.x`, supported beta surfaces may change only with release notes,
upgrade guidance, and a compatibility decision. Removal of a supported surface
requires at least one beta release of notice unless the surface is unsafe or
unusable. Internal surfaces may change without deprecation.

### Compatibility inventory

Create a checked-in inventory grouped by boundary rather than pretending each
thin forwarding module is an independent product. Every group records:

- owning package and replacement import;
- all forwarding modules in the group;
- current callers or compatibility tests;
- support window (`through 0.1.0b6` for the initial inventory);
- removal condition (zero supported docs and zero non-compatibility callers);
- earliest removal release (never earlier than `0.1.0b7`).

No shim is removed in this track. The inventory converts accidental permanence
into an explicit, testable migration queue.

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

## Alternatives considered

- **Leave support implicit until 1.0.** Rejected because the wheel already
  distributes several top-level packages and compatibility shims; ambiguity is
  already imposing maintenance cost.
- **Freeze every import present in the wheel.** Rejected because packaging
  implementation units are not all intended libraries and a blanket promise
  would prevent needed beta refactoring.
- **Delete the shims before b6.** Rejected because compatibility tests and
  documented historical paths still exercise them, while the release candidate
  needs stabilization rather than broad churn.

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
- Every known compatibility-shim group has a removal condition and earliest
  release.
- `agent_waits` has documented ownership and a passing secondary dependency
  regression.
- One exact b6 candidate SHA has complete local qualification evidence, with
  publication and the real-turn smoke still truthfully marked pending.
