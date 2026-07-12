# Architecture Hardening — Paused Handoff

Date: 2026-07-11

## Resume point

- Repository: `/Users/Monsky/Documents/Codex/2026-07-11/agent-maintainer-strict-burndown`
- Branch: `refactor/attention-priority-provenance`
- Head: `8adfd71` (`feat: label attention context relevance`)
- Upstream base: `origin/main` at `a5c5d43`
- Worktree state at handoff: clean and five commits ahead of `origin/main`
- Current branch is not pushed and has no pull request.

Read these before resuming:

- `AGENTS.md`
- `AGENTS.agent-maintainer.md`
- `docs/superpowers/specs/2026-07-11-attention-priority-provenance-design.md`
- `docs/superpowers/plans/2026-07-11-attention-priority-provenance.md`
- This handoff

## Completed and merged before this branch

- PR #385 merged roadmap/API boundaries and the beta exact-version policy as
  `ef9f234`.
- PR #386 merged the durable verifier wait lifecycle as `a5c5d43`.
- The user explicitly confirmed that this is a beta product. Do not add
  compatibility shims or deprecation machinery for these changes.

## Active branch commits

1. `1f17d3e fix: retain required attention paths`
2. `347c4e9 fix: bound attention priority notes`
3. `af2036b feat: accept attention priority paths`
4. `7c31af7 fix: normalize attention CLI priority parsing`
5. `8adfd71 feat: label attention context relevance`

Tasks 1 and 2 have passed independent architecture/code-quality review.

Task 3a is implemented and locally verified at `8adfd71`, but it has not yet
received independent review. It adds attention schema version 1, labels
entries as `direct`, `inferred`, or `background`, preserves direct facts when
the ledger has no score, and prevents background-only selections from creating
tight risk notes.

## Verification evidence

- Task 1: all 25 attention-builder tests passed; targeted Ruff passed; strict
  Pyright analyzed 742 files with zero diagnostics; final review approved.
- Task 2: 32 attention CLI/builder tests passed; targeted Ruff and format
  passed; strict Pyright analyzed 742 files with zero diagnostics; final review
  approved.
- Task 3a: eight context-pack/hook tests passed; targeted Ruff and format
  passed; strict Pyright analyzed 742 files with zero diagnostics; precommit
  passed.
- `git diff --check` passed before each commit.
- The full `just v` gate has **not** run on this branch yet.

Task 3a focused verification:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/attention/test_attention_context_pack.py \
  tests/hooks/test_hook_output_invariants.py -q
PYTHONPATH=src .venv/bin/ruff check \
  src/agent_maintainer/context/pack/attention.py \
  tests/attention/test_attention_context_pack.py
PYTHONPATH=src python3 -m agent_maintainer.runners.pyright
```

## Exact next slice

First, independently review `7c31af7..8adfd71`. Do not call Task 3 complete
until that review is clean.

Then implement Task 3b from the approved plan:

1. Add keyword-only `requested_paths` plumbing to `attention_payload` and
   `repair_facts_with_attention`.
2. Pass `ContextPackRequest.files` from `build_context_pack`.
3. Confine requested paths to the workspace, normalize them to repository-
   relative POSIX paths, and omit unsafe/outside paths without reading them.
4. Treat valid requested files as `direct`, including an unscored direct entry
   when the ledger does not contain the file.
5. Add the planned explicit-request regression in
   `tests/attention/test_attention_context_pack.py`.
6. Update `src/agent_context/attention_rendering.py` so a nullable score renders
   as `unscored`.
7. Run the context-pack and hook-output tests, targeted Ruff/format, and strict
   Pyright. Commit the bounded slice, then review the integrated Task 3 range.

Likely Task 3b files:

- `tests/attention/test_attention_context_pack.py`
- `src/agent_maintainer/context/pack/attention.py`
- `src/agent_maintainer/context/pack/builder.py`
- `src/agent_context/attention_rendering.py`

The test fixture in `test_attention_context_pack.py` now writes a workspace-
relative `log_path`. This is intentional: the old absolute fixture was refused
by input safety and never actually exercised inferred log-path selection.

## After Task 3

1. Complete Task 4 documentation and roadmap reconciliation.
2. Run the full `just v` gate. It may return a durable pending wait; follow the
   exact emitted sweep command until terminal rather than starting a new wait.
3. Perform the full branch review, push, open the pull request, wait for hosted
   checks, and merge only when green.
4. Start the domain-aware Archguard chunk from updated `main`.
5. Run beta-6 qualification as the final architecture-hardening chunk.
6. Produce the final audit/roadmap handoff.

## Product guardrail

Keep attention work narrow. The accepted direction retains direct evidence and
adds provenance; it does not add aggressive pruning or self-reinforcing
heuristics. Before treating attention as a product win, beta qualification
should compare old and new behavior on representative repair tasks using:

- relevant-file recall;
- task/test success rate;
- token cost;
- latency; and
- false or overconfident risk-note rate.

If the new path increases tunnel vision or does not improve outcomes, disable
or revert the selection behavior instead of expanding the heuristic.

## Tooling notes

- Serena LSP is useful for navigation, but its index has gone stale after new
  symbols. Canonical tests and strict Pyright are authoritative.
- The primary JetBrains-backed Serena transport was unavailable in this run.
- The implementation subagent exhausted its bounded assignment capacity.
  Reuse it only for a much smaller task or perform Task 3b locally.
- The `architecture_boundaries` reviewer remains the appropriate independent
  read-only reviewer.
- Scratch SDD files under `.superpowers/sdd/` are ignored, but Markdownlint can
  still scan ignored Markdown files.
- Keep user updates at milestone level; the user explicitly found parser-level
  narration too granular.

## Stop conditions

Pause rather than widen scope if Task 3b requires unrelated context-pack
refactoring, direct paths cause arbitrary file reads, the full verifier is not
terminal, or attention qualification shows worse recall or task outcomes.
