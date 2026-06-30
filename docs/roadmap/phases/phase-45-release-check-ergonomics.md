# Phase 45: Release-Check Ergonomics

## PR Title

```text
feat: add release-check command
```

## Goal

Remove the PATH-dependent `just` friction from release verification while keeping
the existing `just release-check` workflow.

## Requirements

- Add a package-native release check command or documented wrapper that runs the
  same release-only tests as `just release-check`.
- Keep `just release-check` working.
- Update release docs to prefer the package-native command when the CLI is
  installed and mention `.venv/bin/just` as the local fallback.
- Add tests for command construction if a new CLI command is introduced.

## Acceptance Criteria

- Release-check command works without relying on shell PATH containing
  `.venv/bin`.
- Existing release tests still pass.
- Precommit passes.

---
