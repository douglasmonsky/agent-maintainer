# Phase 42: Pre-Case-Study Hardening Plan

## PR Title

```text
docs: add pre-case-study hardening plan
```

## Goal

Pause future external case studies until the repository hardens the surfaces
that the case studies would otherwise expose: context package boundaries,
agent-facing output volume, release ergonomics, and release-state drift.

## Requirements

- Record `0.1.0b4` release evidence in `docs/releases/0.1.0b4.md`, including
  TestPyPI/PyPI workflow runs, package hashes, GitHub release assets, and smoke
  tests.
- Add explicit pre-case-study roadmap items for:
  - context package boundary split;
  - hook-output invariant tests;
  - release-check ergonomics;
  - release-state drift check.
- Keep future case-study work postponed until those items are complete or explicitly
  deferred.
- Keep this phase documentation-only.

## Out Of Scope

- Do not start measured external case studies in this phase.
- Do not refactor source code in this phase.
- Do not publish another package version in this phase.

## Acceptance Criteria

- Roadmap shows `0.1.0b4` published and smoke-tested.
- Detailed release evidence exists.
- Roadmap has concrete hardening phases before future case-study work.
- Precommit passes.

---
