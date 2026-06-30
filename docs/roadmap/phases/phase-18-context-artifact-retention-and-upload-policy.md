# Phase 18: Context Artifact Retention and Upload Policy

## PR Title

```text
feat: protect context pack artifact retention
```

## Goal

Prevent `.verify-logs/context` from leaking source excerpts through CI artifacts.

## Policy

```text
.verify-logs/manifest.json        upload okay
.verify-logs/LAST_FAILURE.md      upload okay if sanitized/bounded
.verify-logs/*.log                existing policy applies
.verify-logs/context/PACK.md      local-only by default
.verify-logs/context/PACK.json    local-only by default
```

## Config Fields

Add:

```python
context_write_context_packs: bool = True
context_packs_local_only: bool = True
context_pack_contains_source: bool = True
```

## Behavior

If CI upload configuration includes `.verify-logs/` and context packs exist, doctor warns unless packs are explicitly marked upload-safe.

## Tests

Create:

```text
tests/context/test_retention.py
tests/doctor/test_context_pack_upload_policy.py
```

## Acceptance Criteria

- Context pack retention documented.
- Doctor warns on unsafe upload configuration.
- CI upload behavior does not include packs by default.
- Precommit passes.

---
