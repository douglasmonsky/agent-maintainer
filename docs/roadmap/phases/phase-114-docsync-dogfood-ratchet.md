# Phase 114: DocSync Dogfood Seed And Ratchet

Status: complete

## Goal

Begin dogfooding DocSync in this repository without blocking the ongoing
package-extraction refactor. The first step should make DocSync prove its own
core documentation, configuration, source, and test evidence. Broader
repository-wide documentation coverage should be ratcheted only after the
current extraction sequence settles.

## Scope

- Replace the empty `.docsync/trace.yml` with focused, real trace evidence for
  DocSync's own extraction contract.
- Add Markdown object markers to the DocSync extraction notes.
- Add explicit source evidence regions for the DocSync boundary contract,
  boundary tests, and command surface.
- Run DocSync doctor, index, and check against the seeded trace.
- Keep `.docsync/out/` generated and uncommitted.
- Document a later full-doc ratchet that reviews public docs section by section
  and adds evidence only where it improves maintainability.

## Non-Goals

- Do not require all repository documentation to be DocSync-covered in this
  phase.
- Do not make DocSync checks a new blocking verifier gate in this phase.
- Do not change DocSync runtime behavior.
- Do not add graph, vector, GraphQL, wiki, or retrieval features.
- Do not use DocSync as a substitute for ordinary tests or architecture
  contracts.

## Acceptance Criteria

- `.docsync/trace.yml` is non-empty and links at least one document object to
  real source/test/config evidence.
- `python -m docsync doctor` passes.
- `python -m docsync index` writes only generated files under `.docsync/out/`.
- `python -m docsync check --base origin/main` passes for the seeded evidence.
- The roadmap clearly states that full DocSync coverage is a future ratchet,
  not an immediate broad rewrite.
- Existing Agent Maintainer verification remains unchanged.

## Future Ratchet

After the internal package extraction stabilizes:

1. Review public docs in small groups: README/onboarding, diagnostics,
   provider docs, release docs, and architecture docs.
2. Add DocSync objects and claims only for durable user-facing promises or
   high-risk setup instructions.
3. Prefer source/test/config evidence over prose-only self-references.
4. Require evidence updates when linked behavior changes.
5. Consider a non-blocking Agent Maintainer check before making DocSync part of
   regular verification.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync doctor`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync index`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check --base origin/main`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docsync -q`
- `git diff --check`

## Notes For Future Agents

Keep DocSync evidence narrow and durable. A trace entry should protect an
important contract, not mirror every paragraph in docs. When a linked source
region changes, update the corresponding documentation object or create an
attestation with a specific reason.
