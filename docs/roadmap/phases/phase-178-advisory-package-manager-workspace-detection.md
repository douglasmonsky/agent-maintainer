# Phase 178: Advisory Package-Manager And Workspace Detection

Status: complete

## Goal

Report provenance-rich root package-manager and workspace declarations for
TypeScript/JavaScript setup assessment without inferring commands or package
ownership.

## Delivered

- Typed npm, pnpm, Yarn, and Bun declaration and lockfile signals.
- Literal package, pnpm, and explicit Agent Maintainer workspace declarations.
- Stable advisory issues for malformed, unsupported, invalid, and conflicting
  evidence.
- Setup-advisor reasons and prompts that preserve explicit command ownership.
- JSON evidence with file-and-field provenance.

## Safety Boundary

- No inferred command execution, provider enablement, or configuration mutation.
- No workspace glob expansion or nested package ownership inference.
- No package-manager selection when evidence agrees or conflicts.
- TypeScript/JavaScript remains experimental and advisory.

## Next Slice

Knip unused-code and dependency facts, with stable JSON parsing and external
repository evidence, are the next TypeScript/React parity slice.

## Verification

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/assess/test_package_workspace_evidence.py tests/assess/test_evidence.py tests/assess/test_setup_advisor.py tests/docs/test_first_touch_docs.py tests/docs/test_roadmap_docs.py tests/docsync/test_public_doc_trace.py
.venv/bin/python -m docsync check
just v
```
