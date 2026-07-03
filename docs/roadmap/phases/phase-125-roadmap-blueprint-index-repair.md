# Phase 125: Roadmap Blueprint Index Repair

Status: complete

## Goal

Repair the compact roadmap blueprint index so it links every split phase spec
and cannot silently drift when new phase files are added.

## Scope

- Refresh `docs/roadmap/full-roadmap-blueprint.md` from the actual phase files.
- Keep the blueprint as a compact index, not a monolithic implementation spec.
- Add a docs test proving every `docs/roadmap/phases/phase-*.md` file appears
  in the compact index.
- Keep this documentation/test-only.

## Non-goals

- Do not expand the blueprint into detailed phase content.
- Do not alter phase implementation scope.
- Do not change runtime behavior.
- Do not add new roadmap themes.

## Acceptance Criteria

- `full-roadmap-blueprint.md` links all current phase files.
- Future phase files must be added to the index or docs tests fail.
- Existing local Markdown links in the index still resolve.
- Docs and precommit checks pass.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docs/test_roadmap_docs.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
