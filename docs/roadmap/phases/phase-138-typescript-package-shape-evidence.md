# Phase 138: TypeScript Package Shape Evidence

Status: complete

## Goal

Add real Git repository reviewability evidence for common npm, pnpm, Vite, and
Vitest TypeScript/JavaScript project shapes without changing provider behavior
or making TypeScript reviewability blocking.

## Scope

- Extend public `assess reviewability --json` tests against temporary Git
  repositories.
- Cover npm-style and pnpm-style project metadata and lockfiles.
- Cover Vite and Vitest config/test naming shapes.
- Keep package-manager and test-runner commands explicit; do not add
  autodetection.
- Update TypeScript maturation notes and DocSync evidence.

## Non-goals

- No package-manager autodetection.
- No command execution for npm, pnpm, Vite, Vitest, Jest, or other Node tools.
- No starter files.
- No coverage, dependency/security, mutation, or blocking reviewability adapter.
- No new ecosystem.

## Acceptance Criteria

- Real-repo reviewability tests prove npm/Vite/Vitest source-plus-test changes
  remain low-noise.
- Real-repo reviewability tests prove pnpm lockfile/config-only changes do not
  become source-heavy or source-without-test advisories.
- TypeScript maturation docs explicitly mention npm/pnpm/Vite/Vitest real-repo
  shape evidence.
- DocSync trace links the public claim to durable tests.
- Existing TypeScript provider maturity remains experimental/advisory-only.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_typescript_real_repo_reviewability.py tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
