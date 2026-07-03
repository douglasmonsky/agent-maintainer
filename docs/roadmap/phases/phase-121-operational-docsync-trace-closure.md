# Phase 121: Operational DocSync Trace Closure

Status: complete

## Goal

Close the stale roadmap gap after extending DocSync coverage from first-adoption
public docs into the operational docs users and agents follow while installing
hooks, managing context compression, releasing packages, and maintaining
architecture policy.

## Scope

- Confirm `.docsync/trace.yml` includes claims for agent hooks, context
  compression, release checklist, and architecture policy docs.
- Confirm `tests/docsync/test_readme_trace.py` ratchets those objects and claims.
- Update the roadmap so completed operational-doc tracing is not still listed as
  future work.
- Keep this phase documentation-only; no DocSync runtime behavior changes.

## Non-goals

- Do not add graph, vector, GraphQL, wiki, or generated site features.
- Do not replace ordinary tests, Tach contracts, or verifier gates with DocSync.
- Do not trace every subsection of every document in one pass.
- Do not edit generated `.docsync/out/` files.

## Acceptance Criteria

- DocSync check passes.
- Public-doc trace tests include the operational docs claims.
- Roadmap future work no longer says hooks, compression, release, and
  architecture docs are still untraced.
- No runtime behavior changes are made.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docsync/test_readme_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
