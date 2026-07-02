# Phase 112: Agent Context Primitives And Reading Extraction

Status: complete

## Goal

Start the `agent_context` package extraction with the pure, reusable context
primitives and reading utilities while preserving all existing
`agent_maintainer.context.*` import paths through compatibility shims.

## Why This Is Split From Full Context Extraction

The full context package currently includes product-coupled code that reads
Agent Maintainer config, ratchet baselines, and verifier artifact constants.
Moving the entire package in one PR would either make `agent_context` import
back into `agent_maintainer` or force unrelated adapter refactors. This phase
extracts the safe foundation first and leaves context-pack CLI/ratchet/artifact
adapter work for the next phase.

## Scope

- Create `src/agent_context/`.
- Move pure primitives:
  - `budget.py`
  - `estimate.py`
  - `failures.py`
  - `formatting.py`
  - `models.py`
- Move reading utilities that can remain independent:
  - `reading/diff.py`
  - `reading/diff_classify.py`
  - `reading/diff_git.py`
  - `reading/file_safety.py`
  - `reading/files.py`
  - `reading/logs.py`
  - `reading/python_outline.py`
- Keep old import paths under `agent_maintainer.context.*` as shims.
- Update active Agent Maintainer imports to use `agent_context` where the
  moved modules are consumed.
- Update Tach, config paths, generated guidance, and architecture decision notes
  for the new package root.
- Add direct tests for the new package paths and compatibility tests for old
  imports.

## Boundary Note

`failures.py` currently reads Agent Maintainer's verifier manifest. In this
phase it should stop importing `agent_maintainer.verify.artifacts` and instead
own the generic default manifest filename it reads. That keeps the new package
independent while preserving the existing manifest path.

## Non-Goals

- Do not move `agent_maintainer.context.cli`.
- Do not move context-pack builder/rendering/compression/ratchet modules yet.
- Do not change context pack JSON, markdown, repair capsule wording, hook
  output, or verifier semantics.
- Do not add vector, GraphQL, wiki, retrieval, or DocSync knowledge-graph code.

## Acceptance Criteria

- `src/agent_context/` exists and does not import `agent_maintainer`.
- Existing `agent_maintainer.context.budget`, `.models`, `.formatting`, and
  `.reading.*` imports continue to work.
- Active code that can safely use the new package imports it directly.
- Tach exact mode accounts for `agent_context` without broad root buckets.
- `[tool.agent_maintainer]` paths include `src/agent_context` where relevant.
- Direct new-package tests and old-path compatibility tests pass.
- Normal verification profiles still pass with only existing expected warnings.

## Verification

- Focused context tests passed for budget, models, formatting, failures,
  estimates, file safety, files, logs, diffs, Python outlines, exact facts, and
  compatibility imports.
- `python -m agent_maintainer guidance --check` passed.
- `python -m agent_maintainer change-plan check` passed.
- `tach check --exact` passed.
- `python -m agent_maintainer verify --profile precommit` passed with expected
  structure/change-budget warnings.
- `python -m agent_maintainer verify --profile full` passed with expected
  structure/change-budget warnings.
- `python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main`
  passed with expected structure/change-budget warnings.
- `python -m agent_maintainer verify --profile security` passed.
- `python -m agent_maintainer verify --profile manual` passed.

## Follow-Up

Next phase should extract or adapter-wrap context-pack builder/rendering,
compression, failure records, and ratchet context only after product dependencies
are isolated cleanly.
