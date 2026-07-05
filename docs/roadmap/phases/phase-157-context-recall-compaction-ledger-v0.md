# Phase 157: Context Recall Compaction Ledger v0

Status: complete

## Goal

Persist high-value externalized decisions, constraints, and artifact handles across compaction and long-running work.

## Primary ROI

Cost medium-high, quality medium, speed medium-high: recovery should not depend on chat memory.

## Scope

- Create context recall and ledger modules.
- Add `context ledger add` and `context recall` commands with kind and query filters.
- Write `.verify-logs/context/ledger.jsonl`.
- Ledger items store externalized decisions, failures, artifacts, tasks, constraints, summaries, values, related paths, and rehydrate commands.
- No hidden chain-of-thought, embeddings, or model calls.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `tests/context/test_recall_ledger.py`
- `python3 -m agent_maintainer context ledger add --kind decision --summary "test decision"`
- `python3 -m agent_maintainer context recall --kind decision`
- `python3 -m agent_maintainer verify --profile fast`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 157. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
