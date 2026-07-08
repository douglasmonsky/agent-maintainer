# Phase 166: TypeScript Package-Manager And Workspace Evidence

Status: complete

## Goal

Add TypeScript/React package-manager and workspace reviewability evidence
without promoting TypeScript/React advisories to blocking gates.

## Scope

- Add temporary Git repository evidence for a pnpm workspace-shaped diff.
- Cover root package metadata, workspace metadata, lockfile metadata, package
  metadata, workspace TSX source, and workspace TSX test files.
- Classify `pnpm-workspace.yaml` as TypeScript workspace config.
- Exercise the public `assess reviewability --json` command.
- Update TypeScript maturation notes with the workspace baseline.
- Keep TypeScript/React provider behavior advisory-only.

## Non-Goals

- No package-manager autodetection.
- No npm, pnpm, Vite, Next.js, Jest, Vitest, or React command execution.
- No framework-specific generated-file policy.
- No blocking reviewability gate.
- No provider promotion.

## Acceptance Criteria

- Real-repo reviewability tests prove pnpm workspace-shaped changes remain
  low-noise.
- Workspace config, lockfile, package metadata, source, and test roles are
  classified with zero unclassified files.
- TypeScript maturation notes mention the workspace evidence and remaining gap.
- Existing TypeScript provider maturity stays experimental/advisory-only.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_typescript_real_repo_reviewability.py tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
