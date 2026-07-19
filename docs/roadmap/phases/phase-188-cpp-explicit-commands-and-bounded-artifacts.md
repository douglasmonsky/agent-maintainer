# Phase 188: C/C++ Explicit Commands And Bounded Artifacts

Status: planned

## Goal

Execute the five repository-owned C/C++ checks through the existing verifier
while preserving exact command authority and bounded sanitized evidence.

## Scope

- Add `cpp-format`, `cpp-static-analysis`, `cpp-build`, `cpp-test`, and
  `cpp-coverage` checks.
- Add typed repeated report declarations with exact paths and byte limits.
- Resolve system executables and explicit repository wrappers safely.
- Preserve profile selection and explicit optional skips.
- Link every declared report to its producing command outcome.
- Emit versioned bounded runner artifacts without raw report bodies.
- Add Linux, macOS, and Windows command-contract fixtures.

## Non-Goals

- No report-format parsing beyond provenance and envelope validation.
- No shell strings, pipes, redirects, inferred presets, or inferred targets.
- No tool installation, CMake configuration, build-directory creation, or
  baseline mutation.
- No blocking C/C++ policy.

## Acceptance Criteria

- Empty command arrays skip explicitly; configured unsafe or missing
  executables fail with actionable facts.
- Repository wrappers cannot escape through absolute paths, traversal,
  symlinks, or non-regular files.
- Required missing, stale, malformed-envelope, or oversized reports fail
  closed; optional absence stays visible.
- Artifacts are deterministic, bounded, sanitized, and tied to one run.
- All three platform fixtures exercise equivalent provider contracts.

## Phase 189 Handoff

Consume only the validated report envelopes written by the runner. Do not
reopen arbitrary configured paths from repair-fact consumers.
