# Phase 111: Agent Repair Facts Internal Package Extraction

Status: complete

## Goal

Extract repair-fact payload normalization, parser implementations, and parser
dispatch into a new internal sibling package, `agent_repair_facts`, while
preserving current Agent Maintainer context-pack behavior and old import paths.

## Scope

- Create `src/agent_repair_facts/` as the owner of normalized repair facts.
- Move parser payload helpers, structured artifact parsers, log parsers, pytest
  parsers, and TypeScript parser adapters into the new package.
- Keep compatibility shims under `agent_maintainer.context.pack.*` for moved
  modules during the first extraction pass.
- Update Agent Maintainer context-pack code to depend on the new package.
- Update Tach ownership, source/config paths, guidance, and architecture notes
  for the introduced package root.
- Add direct tests for the new package and compatibility tests for old import
  paths.

## Non-Goals

- Do not extract `agent_context`, `agent_run_artifacts`, or hook packages in
  this phase.
- Do not change context pack JSON shape, repair capsule wording, hook output, or
  verifier result semantics.
- Do not remove old import paths yet.
- Do not add vector, GraphQL, wiki, retrieval, or DocSync knowledge-graph code.
- Do not publish a separate `agent-repair-facts` distribution.

## Acceptance Criteria

- `src/agent_repair_facts/` exists and owns repair-fact payload/parser logic.
- Existing imports from `agent_maintainer.context.pack.fact_*` continue to work
  through thin shims.
- `agent_maintainer.context.pack.exact_facts` uses the new repair-facts package
  for parser dispatch and payload normalization.
- Tach exact mode accounts for the new package without broad root buckets.
- `[tool.agent_maintainer]` paths include the new package where source,
  package, coverage, file-length, structure, vulture, and Semgrep checks need
  it.
- Generated `AGENTS.agent-maintainer.md` is refreshed if config paths change.
- No generated logs, `mutants/`, `__pycache__`, `*.pyc`, or duplicate artifact
  files are committed.

## Verification

- Focused context/repair-fact tests passed:
  `tests/docs/test_roadmap_docs.py`, `tests/context/test_exact_facts.py`,
  and `tests/core/test_typescript_structured_output.py`.
- Direct import compatibility tests for new and old module paths were added to
  `tests/context/test_exact_facts.py`.
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

## Notes For Future Codex Tasks

- Start from Phase 110 baseline and the internal package boundary ADR.
- Move one boundary only. If extraction of repair facts reveals pressure to move
  context pack rendering, stop and open a follow-up phase instead.
- If a proposed dependency requires `agent_repair_facts` to import
  `agent_maintainer`, redesign the boundary or keep the code in
  `agent_maintainer` for now.
