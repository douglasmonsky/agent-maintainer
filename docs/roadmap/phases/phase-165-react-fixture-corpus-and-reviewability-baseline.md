# Phase 165: React Fixture Corpus And Reviewability Baseline

Status: complete

## Goal

Add a React-shaped TypeScript/JavaScript reviewability evidence baseline without
promoting TypeScript/React advisories to blocking gates.

## Scope

- Add temporary Git repository evidence for a React app-shaped diff.
- Cover TSX source, TSX test, React dependencies, and entrypoint files.
- Exercise the public `assess reviewability --json` command.
- Update TypeScript maturation notes with the React baseline.
- Keep TypeScript/React provider behavior advisory-only.

## Non-Goals

- No package-manager autodetection.
- No Vite, Next.js, Jest, Vitest, or React command execution.
- No framework-specific generated-file policy.
- No blocking reviewability gate.
- No provider promotion.

## Acceptance Criteria

- Real-repo reviewability tests prove React-shaped TSX source-plus-test changes
  remain low-noise.
- The React fixture classifies source/test roles and React dependency metadata
  without advisory findings.
- TypeScript maturation notes mention the React evidence and remaining gap.
- Existing TypeScript provider maturity stays experimental/advisory-only.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_typescript_real_repo_reviewability.py tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
