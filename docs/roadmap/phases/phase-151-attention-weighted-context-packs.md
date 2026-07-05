# Phase 151: Attention-Weighted Context Packs

Status: complete

## Goal

Use attention-ledger signals to improve context-pack ordering, warnings, and next-action selection without expanding raw context by default.

## Primary ROI

Cost high, quality high, speed high: context packs can route attention without getting larger.

## Scope

- Add optional `attention` block to context-pack payloads without removing existing keys.
- Attach attention scores for files mentioned by exact repair facts.
- When no exact file fact exists, use failed-check log paths and manifest data to attach relevant attention entries.
- Pointer output may include up to three compact risk notes for high-attention files.
- Keep hook output under configured budget.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `tests/context/test_packs.py`
- `tests/attention/test_attention_context_pack.py`
- Context pack works without ledger
- Pointer includes bounded risk note when appropriate
- `python3 -m agent_maintainer attention update`
- `python3 -m agent_maintainer context pack`
- `python3 -m agent_maintainer verify --profile fast`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 151. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
