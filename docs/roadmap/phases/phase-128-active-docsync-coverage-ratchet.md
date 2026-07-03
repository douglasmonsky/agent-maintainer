# Phase 128: Active DocSync Coverage Ratchet

Status: complete

## Goal

Make DocSync dogfood the active documentation set at the overview level, not only
the README and a hand-picked subset of public docs.

## Scope

- Add a coverage ratchet that requires active docs to be listed in
  `.docsync/trace.yml`.
- Require each active traced doc to have a live overview object marker.
- Exclude roadmap history, archives, ADRs, and graphics assets from this first
  inventory ratchet because those files change frequently or are not product
  claims.
- Add overview markers and trace entries for currently active docs that were not
  yet covered.
- Keep claim/evidence expansion incremental and section-level.

## Non-goals

- Do not require every paragraph to have a DocSync claim.
- Do not add DocSync coverage for roadmap phase files, archived history, ADRs,
  or generated/output folders in this pass.
- Do not change DocSync runtime semantics.
- Do not rewrite public docs beyond adding hidden object markers.

## Acceptance Criteria

- Active docs have a trace document entry.
- Active docs have a live `.overview` object entry.
- Public DocSync trace tests fail if a new active doc is added without trace
  coverage.
- `docsync check` passes.
- Precommit passes.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
