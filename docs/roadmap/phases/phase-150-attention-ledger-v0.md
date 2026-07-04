# Phase 150: Attention Ledger v0

Status: complete

## Goal

Create a deterministic local file-level attention ledger that scores repo objects by risk and usefulness for future agent calls.

## Primary ROI

Cost high, quality high, speed medium-high: high-value files should surface without agents rereading the whole repo.

## Scope

- Create `src/agent_maintainer/attention/` with models, signals, builder, rendering, and CLI.
- Add `attention update`, `attention top`, `attention explain <path>`, and `attention changed`.
- Write `.verify-logs/attention/files.json`.
- Use deterministic inputs only: runtime events, manifests, DocSync trace/index, file-baseline report, git changed counts, path heuristics.
- Normalize component scores to 0..1 and include reasons for every non-zero component.

## Non-Goals

- Do not broaden the product boundary beyond this phase's stated surface.
- Do not paste raw logs or large artifacts into agent-facing output.
- Do not weaken Tach, DocSync, guidance, or verifier gates to make the phase pass.
- Do not skip Phase 145 prerequisites when this phase depends on runtime event contract completion.

## Verification And Acceptance Criteria

- `tests/attention/test_attention_signals.py`
- `tests/attention/test_attention_builder.py`
- `tests/attention/test_attention_cli.py`
- Missing-input and deterministic JSON cases
- `python3 -m agent_maintainer attention update`
- `python3 -m agent_maintainer verify --profile fast`
- `tach check --exact`

## Notes For Future Tasks

Treat this file as the implementation authority for Phase 150. Keep the PR scoped to this phase unless the user explicitly asks to bundle phases.
