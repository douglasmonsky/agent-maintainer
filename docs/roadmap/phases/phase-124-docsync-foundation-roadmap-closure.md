# Phase 124: DocSync Foundation Roadmap Closure

Status: complete

## Goal

Close the stale DocSync foundation section in the main roadmap. The foundation
is implemented and dogfooded, so the roadmap should describe current
capabilities and evidence instead of an old planned execution list.

## Scope

- Rewrite the top-level DocSync foundation roadmap section as completed
  current state.
- Point readers to implementation evidence in `docs/docsync-extraction.md`,
  `.docsync/trace.yml`, and `tests/docsync/`.
- Keep the knowledge graph, vector index, GraphQL layer, and wiki projection
  explicitly out of scope on `experiment/docsync-knowledge-graph`.
- Keep this documentation-only.

## Non-goals

- Do not change DocSync runtime behavior.
- Do not add new DocSync claims.
- Do not move DocSync files.
- Do not revive graph, vector, GraphQL, or wiki prototypes.
- Do not change generated guidance.

## Acceptance Criteria

- `docs/ROADMAP.md` no longer describes DocSync foundation work as a pending
  execution order.
- The section lists implemented DocSync capabilities.
- The section points to current evidence and dogfood phases.
- Docs checks and DocSync checks pass.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docs/test_roadmap_docs.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
