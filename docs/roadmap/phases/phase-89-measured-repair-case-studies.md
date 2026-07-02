# Phase 89: Measured Repair Case Studies

Status: complete in PR.

## Goal

Promote the measured proof harness from Future Work into the numbered roadmap
and document small, reproducible repair-loop case studies with real command
evidence.

## Scope

- Add measured case-study docs for context-safe repair loops.
- Record commands, observed outputs, and fixture limits.
- Link case studies from README and roadmap indexes.
- Fix stale commands in the context-safe ratchet example README.

## Non-Goals

- No verifier behavior changes.
- No new scanners.
- No new example applications.
- No raw diagnostic logs committed.
- No claims beyond measured fixture evidence.

## Deliverables

- `docs/case-studies/README.md`
- `docs/case-studies/split-large-legacy-file.md`
- `docs/case-studies/context-safe-ratchet-repair.md`
- README links to the measured case studies.
- Roadmap and blueprint indexes list Phase 89.

## Acceptance Criteria

- Case studies use reproducible fixture commands.
- Claims are measured and scoped to the examples.
- Example commands use the current ratchet CLI.
- Markdown/docs checks pass.
- `verify --profile precommit` passes.

## Verification

Run:

```bash
git diff --check
markdownlint-cli2 docs/case-studies/*.md \
  docs/roadmap/phases/phase-89-measured-repair-case-studies.md
python -m agent_maintainer verify --profile precommit
```
