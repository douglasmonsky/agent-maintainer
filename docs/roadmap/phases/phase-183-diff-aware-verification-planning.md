# Phase 183: Diff-Aware Verification Planning And Path-Risk Policy

Status: in progress

## Goal

Turn Agent Maintainer into the repository-aware control layer that maps a Git
diff to exact affected units, named evidence, review categories, configured
checks, and canonical verification profiles without suppressing existing
verifier gates.

## Scope

- Add strict repository-relative paths and segment-aware policy globs.
- Preserve adds, modifications, copies, renames, deletions, and type changes
  through a NUL-delimited Git name-status adapter.
- Load versioned `.agent-maintainer/path-risk.toml` policy and validate exact
  configured profile and check names.
- Resolve conservative Python package, TypeScript workspace, Gradle module, and
  repository fallback units.
- Evaluate rule-local changed-path evidence with destination-only satisfaction.
- Render deterministic human and `schema_version = 1` JSON reports.
- Expose `agent-maintainer verify-plan` with exact `0`, `1`, and `2` statuses.
- Add an optional `verification-plan-policy` gate to fast, precommit, full, and
  CI profiles when repository policy exists.

## Principal Files

- `src/agent_maintainer/verification_plan/`
- `src/agent_maintainer/core/repo_paths.py`
- `src/agent_maintainer/ecosystems/git_changes.py`
- `src/agent_maintainer/catalogs/catalog.py`
- `src/agent_maintainer/catalogs/global_checks.py`
- `src/agent_maintainer/cli.py`
- `.agent-maintainer/path-risk.toml`
- `docs/architecture/decisions/2026-07-18-diff-aware-verification-planning.md`
- `tests/verification_plan/`

## Non-Goals

- No dynamic skipping or suppression of configured verifier gates.
- No check execution inside the planner.
- No compatibility/version-bump inference or failure classification.
- No executable Gradle settings interpretation or package-manager inference.
- No provider promotion or new runtime dependency.

## Acceptance Criteria

- Unsafe policy paths, malformed globs, unknown names, and ambiguous catalog
  identities fail closed.
- Rename/copy source and destination paths and deleted paths trigger policy;
  only current/destination paths satisfy evidence.
- Overlapping rules accumulate without order-dependent loss.
- Identical facts produce byte-identical JSON with no timestamp.
- The public CLI and optional catalog gate preserve exact exit semantics.
- The repository's own policy is satisfied by the implementation diff.
- Focused tests, exact Tach, Archguard, DocSync, a fresh full verifier, one
  independent review, and protected hosted checks pass before completion.

## Verification Evidence

Focused test, architecture, documentation, full-verifier, independent-review,
and protected-PR evidence will be recorded here only after each result exists.
