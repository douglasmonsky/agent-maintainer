# Phase 176: TypeScript/React Parity Roadmap

Status: active

## Goal

Define the TypeScript/React parity roadmap as an integration-branch track that
can be built outside `main` and merged back only after promotion criteria are
met.

## Scope

- Add a detailed TypeScript/React parity roadmap that maps Python-provider
  capabilities to TypeScript/React candidates.
- Record which candidates have strong replacements, partial replacements, or no
  known replacement.
- Define focused implementation slices for package detection, Knip, OSV,
  dependency boundaries, LCOV diff coverage, React lint rules, generated-file
  policy, StrykerJS, and blocking-gate promotion.
- Document that this track builds on `codex/react-typescript-parity-roadmap`
  before a final merge back to `main`.
- Update the compact roadmap index and active tracker so the current TypeScript
  work reflects phases 168 through 175 already landed.

## Non-Goals

- No new TypeScript/React adapter implementation.
- No package-manager command inference.
- No new dependency.
- No blocking TypeScript/React gate.
- No merge back to `main` during this planning phase.

## Acceptance Criteria

- The roadmap names the integration branch strategy and final merge condition.
- The parity table covers format, lint, typecheck, test, coverage,
  architecture, dead code, dependency, security, secrets, complexity, mutation,
  SBOM, license, docs, React hooks, accessibility, Testing Library, and
  generated-file policy surfaces.
- The implementation slices are small enough to become focused PRs.
- Root roadmap and compact phase index point to the new phase.
- Roadmap documentation tests pass.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docs/test_roadmap_docs.py tests/docs/test_first_touch_docs.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
git diff --check
```
