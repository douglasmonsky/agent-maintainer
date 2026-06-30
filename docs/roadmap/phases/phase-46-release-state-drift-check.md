# Phase 46: Release-State Drift Check

## PR Title

```text
feat: add release state drift check
```

## Goal

Make version drift visible before release: package metadata, changelog, Git tags,
GitHub releases, TestPyPI, and PyPI should not silently disagree.

## Requirements

- Add a non-default release/state command or doctor support that reports:
  - local package version;
  - latest matching changelog entry;
  - local/remote Git tag presence;
  - GitHub release presence;
  - TestPyPI and PyPI latest versions when network access is allowed.
- Keep network checks opt-in or release-profile only.
- Document the command in `docs/release-checklist.md`.

## Acceptance Criteria

- Unit tests cover local parsing and network-disabled behavior.
- Release checklist includes the drift check.
- Precommit passes.

---
