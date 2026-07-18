# Phase 179: TypeScript Knip Unused-Code And Dependency Facts

Status: complete

## Goal

Turn explicitly configured Knip JSON output into bounded TypeScript repair
facts and compact summaries without inferring repository commands or promoting
the provider.

## Delivered

- Root `typescript_knip_command` and workspace-owned commands with stable
  `typescript-knip:<workspace>` names.
- Root `typescript_knip_profiles` defaulting to `full` and `ci`, outside
  `precommit` by default.
- Facts for unused files, exports, types, dependencies, binaries, unlisted
  dependencies, and unresolved imports or binaries.
- Narrow workspace-name normalization for existing TypeScript lint, typecheck,
  test, and Knip facts.
- Deterministic sorting before retaining at most 500 normalized findings.
- Compact summaries bounded to 50 total lines and exact context packs retaining
  their existing 5-fact-per-check limit.

## Command And Error Boundary

- The provider runs only the configured command array and never appends
  `--reporter json`, selects a package manager, or enables Knip automatically.
- Agent Maintainer preserves the configured exit status: exit `0` passes, while
  exits `1` and `2` fail normally.
- Malformed JSON or unsupported shapes produce no structured facts; the normal
  bounded raw log remains authoritative.
- Absolute and parent-traversal paths are rejected; only normalized
  repository-relative paths can enter repair context.
- No Agent Maintainer thresholds, `--no-exit-code`, autofix, or Knip version
  enforcement are added.

## Evidence

- Synthetic fixtures cover all supported categories, malformed neighbors,
  ignored categories, deterministic order, and bounds.
- TanStack Query at `97db5d244715642fb63d9ce78566aa632cdfdc07`
  produced an empty issue set with Knip 6.1.1.
- Astro at `91992ef2ccd9a90fa4270633eb4f5d3b811bf315` produced 11
  supported unresolved findings with Knip 5.82.1.
- Both captures used frozen pnpm lockfiles with lifecycle scripts disabled and
  retain config/lockfile hashes without local paths or dependency trees.

TypeScript/JavaScript remains experimental. OSV dependency scanning is the next
parity slice.

## Verification

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/repair_facts/test_typescript_knip_facts.py tests/core/test_typescript_structured_output.py tests/assess/test_typescript_knip_external_fixtures.py tests/docs/test_first_touch_docs.py tests/docs/test_roadmap_docs.py tests/docsync/test_public_doc_trace.py
.venv/bin/python -m docsync check
just v
```
