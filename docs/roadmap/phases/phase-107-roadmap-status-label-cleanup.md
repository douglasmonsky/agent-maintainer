# Phase 107: Roadmap Status Label Cleanup

## Status

Completed.

## Goal

Make `docs/ROADMAP.md` read as an accurate recovery tracker by removing stale
`Next:` labels from already-completed sections. The roadmap should not imply
completed phases are still the next active work.

## Scope

- Rename completed `## Next:` section headings to completed-state wording.
- Rename stale `Planned work:` labels where the item is already checked off.
- Keep numbered phase history intact.
- Keep detailed phase files unchanged unless a link target or status label
  requires correction.

## Non-Goals

- No source code changes.
- No roadmap scope changes.
- No new implementation phase beyond this cleanup.
- No deletion of historical completed phase summaries.

## Acceptance Criteria

- `docs/ROADMAP.md` has no completed sections labeled `## Next:`.
- Completed checkbox groups are not introduced by `Planned work:`.
- The only active-looking work in `docs/ROADMAP.md` is future guidance, not
  completed phase history.
- Markdown lint passes.

## Verification

- `rg -n "^## Next:|Planned work: - \\[x\\]|Planned work:" docs/ROADMAP.md`
- `npx --no-install markdownlint-cli2 docs/ROADMAP.md docs/roadmap/full-roadmap-blueprint.md docs/roadmap/phases/phase-107-roadmap-status-label-cleanup.md`
- `git diff --check`
