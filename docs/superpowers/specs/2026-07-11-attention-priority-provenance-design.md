# Attention Priority Retention and Provenance Design

**Date:** 2026-07-11

**Status:** Approved direction, written contract

## Problem

The attention builder deterministically samples at most 5,000 tracked paths
before it evaluates changed files or verifier artifacts. A relevant file can
therefore disappear before scoring. Context-pack selection then falls back to
unrelated top-ledger entries when an exact fact is absent from that sample, and
the payload gives consumers no way to distinguish direct evidence from inferred
or background context.

## Goals

- Retain changed, verifier-failure, exact-fact, and explicitly requested paths
  even when a large repository exceeds the normal scoring cap.
- Keep background sampling deterministic and bounded.
- Label context entries as `direct`, `inferred`, or `background`.
- Never place background-only attention notes in tight hook output.
- Preserve safe path normalization and bounded artifact reads.

## Non-goals

- Replacing the attention scoring weights or proving ranking quality.
- Reading unbounded verifier artifacts.
- Treating a high attention score as proof that a file caused a failure.
- Persisting context-pack selection provenance into the repository-wide ledger.

## Chosen architecture

### Priority-aware ledger sampling

The builder will discover tracked paths once. It will calculate changed paths
and verifier-artifact paths against that full tracked inventory before choosing
the scored sample. Artifact bytes remain bounded by the existing read limit.

`AttentionSignalContext.build` will accept normalized required paths. Sampling
reserves every required tracked path, then fills the remaining budget with the
existing deterministic even-spaced sample from non-required paths. Required
paths are never discarded. If their count alone exceeds the nominal cap, the
cap becomes a soft background budget: all required paths are retained and a
performance note records the overflow. Total scored work remains hard-bounded
by the existing `DEFAULT_TRACKED_DISCOVERY_LIMIT` of 10,000 paths; automatic and
explicit required paths must be members of that bounded tracked inventory.

`build_attention_ledger` will also accept explicit priority paths so a caller
that knows user-requested files can preserve them. The attention CLI will expose
a repeatable `--priority-path` option for that contract. Nonexistent, absolute,
escaping, or sensitive explicit paths raise `ValueError`; the CLI renders that
as an argument error with exit code 2. Safe paths that are not in the bounded
tracked inventory are omitted from ledger scoring with a performance note.

### Relevance-aware context payload

Context-pack selection uses this order:

1. Exact-fact and explicitly requested file paths are `direct`.
2. Paths found only in selected logs are `inferred`.
3. Top ledger entries used only because neither direct nor inferred paths were
   available are `background`.

Direct paths confined to the workspace remain in the payload even when an older
ledger omitted them. Such an entry reports `score: null`, empty components, and
a bounded reason explaining that no sampled ledger score was available; it does
not invent a risk score. Every attention block carries `schema_version: 1`.
Existing ledger-backed entries retain their score, components, and reasons.

Risk notes are generated only from `direct` and `inferred` entries. A purely
background fallback can still help an interactive inspection command, but its
`risk_notes` list is empty so tight hooks do not imply causal relevance.

## Data flow

1. Collect the full tracked inventory once.
2. Discover changed and verifier-artifact path sets with bounded inputs.
3. Merge automatic paths with caller-provided priority paths.
4. Reserve required paths and deterministically fill the remaining sample.
5. Score and persist the selected ledger as today, including performance notes.
6. When building a context pack, merge exact facts, requested files, log
   mentions, and ledger fallback in provenance order.
7. Attach score and relevance metadata to matching repair facts.

## Error behavior

- Invalid persisted schema version, file count, duplicate path, non-normalized
  path, non-finite score, or out-of-range score continues to reject the ledger.
- Invalid explicit priority paths fail at the API or CLI boundary and never
  cause arbitrary file reads. Safe untracked paths are noted and omitted from
  ledger scoring.
- A missing or invalid ledger keeps `available=false`; direct repair facts
  remain present elsewhere in the pack and are not replaced by fabricated
  attention data.
- Required-path overflow is visible in performance notes rather than silently
  dropping evidence.

## Alternatives considered

- **Raise the cap.** Rejected because any fixed larger cap preserves the same
  correctness bug and increases routine work.
- **Score the entire repository.** Rejected because large-repository cost is the
  reason the cap exists.
- **Give omitted direct paths a score of 1.0.** Rejected because selection
  provenance is not an attention measurement; `null` is honest and explicit.

## Test strategy

- Write failing sampling tests where changed, failed, first, middle, last, and
  explicitly requested files compete for a tiny cap.
- Prove deterministic output and required-path overflow behavior.
- Prove direct exact/requested entries survive an older capped ledger, inferred
  log entries are labeled, and background fallback emits no risk notes.
- Extend reader validation tests for the context attention schema and nullable
  direct scores without weakening ledger score validation.
- Run attention, context-pack, hook-rendering, strict type, and broad verifier
  checks.

## Acceptance criteria

- No required path is lost solely because of the tracked-file cap.
- Scored work never exceeds the existing 10,000-path discovery ceiling.
- The same inputs produce the same sample and ledger ordering.
- Every context attention entry has exactly one supported relevance label.
- Background-only selection produces no tight risk note.
- Existing safe-read, schema, and score-range guarantees remain intact.
