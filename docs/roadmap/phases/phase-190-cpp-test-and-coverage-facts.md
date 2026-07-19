# Phase 190: C/C++ Test And Coverage Facts

Status: planned

## Goal

Normalize CTest test results and truthful C/C++ coverage artifacts into bounded
repair and changed-line facts without inventing toolchain symmetry.

## Scope

- Parse CTest JUnit XML into suite, case, outcome, bounded message, and duration
  facts.
- Parse LCOV tracefiles into executable-line and branch facts.
- Parse explicitly supported version-declared gcovr JSON.
- Preserve real repository-defined coverage scopes.
- Add advisory changed-line coverage for existing artifacts.
- Emit bounded summaries and exact repair facts from the runner artifact.

## Non-Goals

- No test-runner inference, GoogleTest-specific command, or Catch2-specific
  command.
- No native MSVC coverage parser or automatic coverage conversion.
- No synthesized repository aggregate, default threshold, or blocking ratchet.
- No sanitizer or performance facts.

## Acceptance Criteria

- Unknown gcovr major versions and malformed required evidence fail closed.
- Weighted coverage uses executable lines, never averages percentages.
- Multi-scope output remains separate unless the artifact contains a truthful
  aggregate scope.
- Windows paths, CRLF, missing sources, and unsafe paths are tested.
- Repeated no-change runs produce stable normalized facts.

## Phase 191 Handoff

Select external repositories only after a read-only audit proves that each can
produce a supported artifact without Agent Maintainer rewriting its build.
