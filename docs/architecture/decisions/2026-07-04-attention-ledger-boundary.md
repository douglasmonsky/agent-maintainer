# 2026-07-04: Attention ledger boundary

## Status

Accepted.

## Context

Phase 150 adds local file-level attention scoring so future agent calls can
surface high-value repository objects without rereading broad swaths of the
repo. The score must stay deterministic, local, artifact-backed, and advisory.

The ledger uses existing local evidence: git changes and churn, runtime events,
verifier manifests, DocSync artifacts, file-baseline artifacts, and path
heuristics. It writes `.verify-logs/attention/files.json`.

## Decision

Create `agent_maintainer.attention` as a separate package with:

- `signals` for deterministic local input extraction;
- `builder` for score normalization and ledger persistence;
- `models` for the JSON contract;
- `rendering` for compact text/JSON output;
- `cli` for `attention update`, `attention top`, `attention explain`, and
  `attention changed`.

The package may read local diagnostic artifacts and runtime-event JSONL files.
It must not own verifier execution, context-pack rendering, DocSync checks,
runtime-event writing, or report generation.

## Consequences

Phase 151 can consume `.verify-logs/attention/files.json` when weighting context
packs. The score remains advisory; it does not gate verification and does not
change existing profile behavior.
