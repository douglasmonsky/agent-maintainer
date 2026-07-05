# Phase 163: Attention Ledger Performance Guards

Status: planned

## Goal

Keep attention-ledger scoring cheap enough for large repositories before it
becomes more central to default context-pack selection.

## Scope

- Collect tracked files once per ledger build and pass the collection through
  signal calculations.
- Add artifact read limits for DocSync reports, verifier logs, and other text
  artifacts used by attention signals.
- Add an explicit cap or sampling strategy for very large tracked-file sets.
- Record when attention signals are capped or sampled so context-pack decisions
  remain explainable.
- Add tests proving repeated signal calls do not repeatedly invoke tracked-file
  discovery.

## Non-Goals

- Do not change attention score weights without separate evidence.
- Do not remove attention-weighted context packs.
- Do not add background indexing or daemon behavior.

## Acceptance Criteria

- One tracked-file collection per attention-ledger build.
- Large artifact reads are bounded.
- Very large repositories receive a deterministic cap or sampling path.
- Attention output reports when performance guards affected scoring.
- Existing attention CLI and context-pack tests remain green.

## Notes

This phase responds to the risk that `attention.signals` can repeatedly collect
tracked files and scan text artifacts against every tracked path. That is fine
for this repository, but should be guarded before larger repositories depend on
attention scores by default.
