# PR Summary Verification Artifact

## Status

Accepted.

## Context

Phase 29 adds a bounded GitHub Actions summary at `.verify-logs/pr-summary.md`.
The summary must be generated from the same verifier results that already
produce `manifest.json` and `LAST_FAILURE.md`, then appended to
`$GITHUB_STEP_SUMMARY` in CI.

## Decision

Add `agent_maintainer.verify.pr_summary` as a shared verify module and assign it
explicitly in `tach.toml`.

The module renders markdown from `CheckResult` values and the existing run
context. It does not execute checks, inspect arbitrary repository files, or call
GitHub APIs. CI only appends the already generated bounded artifact.

## Alternatives Considered

- Put all rendering in `verify.artifacts`: rejected because that module already
  owns manifest and failure-note writing and is near the module-member limit.
- Generate the summary as a separate CI command: rejected because failed
  verifier runs should still use the exact same in-process result data.
- Upload context packs directly into the summary: rejected because context packs
  may contain source-bearing local-only data.

## Boundaries

The PR summary renderer may depend on verifier result models and bounded-context
helpers. It must not import orchestration modules, run verifier checks, or read
local-only context packs into GitHub summaries.
