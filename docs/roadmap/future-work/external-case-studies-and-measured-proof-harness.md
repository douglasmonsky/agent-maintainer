# Future Work: External Case Studies and Measured Proof Harness

Status: promoted to
[`Phase 89: Measured Repair Case Studies`](../phases/phase-89-measured-repair-case-studies.md).

This original future-work checklist is retained as provenance. New
implementation work should use the Phase 89 file.

## PR Title

```text
docs: add measured context-safe repair case studies
```

## Metrics

Track:

```text
failure output chars before/after
number of checks failing
ratchet targets resolved
new/worsened violations
PR size
agent repair turns
context expansion commands used
time to first useful repair
final verification result
```

## Add Docs

```text
docs/case-studies/split-large-legacy-file.md
docs/case-studies/context-safe-ratchet-repair.md
```

## Acceptance Criteria

- Case studies use reproducible examples.
- Claims are measured.
- No unverified marketing claims.
- Precommit passes.

---
