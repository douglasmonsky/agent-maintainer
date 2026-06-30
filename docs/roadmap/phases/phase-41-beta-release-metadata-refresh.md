# Phase 41: Beta Release Metadata Refresh

## PR Title

```text
chore: refresh beta release metadata
```

## Goal

Prepare the next beta after the stabilization fixes. The release metadata must
not imply the current implementation still matches the older `0.1.0b3` surface.

## Requirements

- Update `CHANGELOG.md` Unreleased section with context packs, ratchets,
  change plans, compression, PR summaries, policy presets, Archguard impact,
  repair plan, Tach domain contracts, static reports, and stabilization fixes.
- Decide next version, expected `0.1.0b4`, after stabilization phases are
  merged.
- Update package metadata only when ready to tag/publish that beta.
- Document Headroom limitations and any manual extra constraints that remain.

## Out Of Scope

- Do not publish to PyPI in this phase unless explicitly requested.
- Do not add new scanners or feature categories.

## Acceptance Criteria

- Changelog accurately describes post-`0.1.0b3` implementation.
- Versioning decision is recorded before the next tag.
- Release checklist references stabilization completion before publishing.

---
