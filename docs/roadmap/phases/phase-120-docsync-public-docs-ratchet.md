# Phase 120: Public Docs DocSync Ratchet

Status: complete

## Goal

Move DocSync dogfooding beyond README claims into the core public documentation
that users and coding agents follow during first adoption, verification,
diagnostics, ratcheting, scan selection, and provider-status review.

## Scope

- Add DocSync object markers to the highest-value public docs.
- Expand `.docsync/trace.yml` with claims for those documents.
- Link claims to existing source/config/test evidence where practical.
- Extend the DocSync regression test so future edits keep public-doc coverage.
- Keep generated `.docsync/out/` files rebuildable and uncommitted.

## Non-goals

- Do not trace every historical roadmap or ADR in this phase.
- Do not change DocSync runtime behavior.
- Do not add graph, vector, GraphQL, or wiki features.
- Do not make DocSync replace ordinary tests, Tach contracts, or verifier gates.
- Do not overfit trace entries to unstable prose.

## Deliverables

- Object markers for quick start, first-run, diagnostics, supported scans,
  ratcheting, and provider-status docs.
- Expanded `.docsync/trace.yml`.
- Updated DocSync trace regression tests.
- Updated roadmap index.

## Acceptance Criteria

- `docsync check --base origin/main` passes.
- Public-doc trace tests fail if the new object/claim coverage is removed.
- Claims point to durable implementation evidence, not only other prose.
- Markdown and roadmap checks pass.
- Normal precommit verification passes.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync.cli check --base origin/main`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docsync/test_public_doc_trace.py tests/docsync -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docs/test_roadmap_docs.py -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`

## Follow-Up

Continue DocSync coverage for hooks, compression, release, architecture, and
provider-specific docs in small slices. Add new source evidence regions when
existing evidence is too broad to support a public claim.
