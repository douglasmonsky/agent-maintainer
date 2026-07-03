# Phase 143: DocSync Explicit Object End Markers

Status: planned

## Goal

Make DocSync object regions explicit by adding closing object markers that match
the existing evidence start/end pattern.

## Motivation

DocSync evidence regions already use explicit start and end markers. Object
markers currently identify the start of a documentation object, but the end of
the object is implicit. That is workable for current parsing, but it is weaker
for human editing, automated validation, and future documentation refactors.

Explicit object end markers should make scope clear, reduce accidental object
bleed, and allow DocSync to validate malformed or overlapping documentation
objects more directly.

## Scope

- Design a closing marker syntax, likely:
  `<!-- docsync:object.end <object-id> -->`
- Keep existing opening object marker syntax valid.
- Update DocSync parser/indexer to recognize object end markers.
- Add validation for missing, mismatched, nested, or overlapping object regions.
- Add a migration helper or repair command to insert end markers for existing
  active docs.
- Update active docs to include explicit object end markers once the parser
  supports them.
- Update DocSync docs and tests to describe the object-region contract.

## Non-goals

- No change to evidence start/end marker syntax.
- No broad DocSync graph redesign.
- No change to source evidence semantics.
- No generated-output commit from `.docsync/out/`.
- No hard failure for legacy object markers until the migration pass has landed.

## Acceptance Criteria

- DocSync accepts explicit object end markers.
- DocSync reports clear diagnostics for missing, mismatched, nested, or
  overlapping object regions.
- Existing docs can be migrated mechanically.
- Active docs use explicit object end markers after migration.
- Tests cover legacy-compatible parsing, strict parsing, and malformed object
  regions.
- DocSync guidance explains that evidence and object scopes both use explicit
  close markers.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docsync -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
npx --no-install markdownlint-cli2 docs/roadmap/phases/phase-143-docsync-explicit-object-end-markers.md docs/ROADMAP.md docs/roadmap/full-roadmap-blueprint.md
```
