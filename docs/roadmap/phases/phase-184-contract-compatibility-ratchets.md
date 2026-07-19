# Phase 184: Contract Compatibility Ratchets

Status: qualification pending

## Goal

Detect semantic drift in repository-owned configuration, CLI, Python API,
JSON-RPC, and persistence contracts, then require the exact revision, package
version, decision, and migration evidence needed for intentional changes.

## Scope

- Load strict `.agent-maintainer/contracts.toml` policy and canonical generated
  baselines.
- Normalize configuration capabilities, authored CLI manifests, nominated
  Python APIs, and JSON Schema into one descriptor model.
- Classify breaking, compatible additive, and review-required changes with
  stable fingerprints.
- Compare merge-base, checked-in baseline, and live extraction to prevent
  baseline rewrite bypasses.
- Enforce independent contract-revision, package-version, exact-decision, and
  migration-evidence obligations.
- Expose deterministic `contract diff`, `contract check`, and explicit
  `contract snapshot --write` commands with exact exit statuses.
- Make staged pre-commit checks index-authoritative for policy, baseline,
  package version, sources, and migration diffs.
- Add the conditional `contract-compatibility` verifier gate.
- Dogfood five Agent Maintainer beta contracts.

## Principal Files

- `src/agent_maintainer/contracts/`
- `.agent-maintainer/contracts.toml`
- `.agent-maintainer/contracts-baseline.json`
- `config/agent-maintainer-cli.json`
- `schemas/codex-app-server-wait.schema.json`
- `schemas/agent-waits-wait-record.schema.json`
- `tests/contracts/`
- `docs/architecture/decisions/2026-07-18-contract-compatibility-ratchets.md`

## Non-Goals

- No pre-1.0 cross-version compatibility guarantee.
- No automatic source, policy, version, migration, or baseline rewrite.
- No runtime import of arbitrary target modules, target-command execution,
  network access, or shell evaluation.
- No OpenAPI, protobuf, database migration, or arbitrary-language ABI support.
- No failure-history clustering or recurring-failure ownership.

## Acceptance Criteria

- Policy and baseline inputs fail closed and remain repository-confined.
- Deep baseline bodies, non-regular staged blobs, ambiguous index entries, and
  pre-adoption snapshot replacement fail closed with typed invalid reports.
- All extractor families emit deterministic common descriptors.
- Exact semantic findings independently enforce revision, version, decision,
  and migration obligations.
- Current freshness and base-to-live compatibility both pass.
- Public commands preserve `0`, `1`, and `2` exit semantics.
- The optional gate activates only with policy and suppresses no existing gate.
- Agent Maintainer's five dogfood descriptors exactly match live extraction.
- Focused, mutation, architecture, DocSync, full, CI-equivalent, security,
  independent-review, and hosted checks pass before completion.

## Phase 185 Handoff

Phase 185 owns failure intelligence: recurring-failure fingerprints, new versus
pre-existing classification, and machine-readable repair packets. It consumes
Phase 184's deterministic contract repair facts without changing compatibility
policy. The external three-to-five-repository cohort continues in parallel as a
measurement track for activation cost, false positives, repair iterations, and
retained use.
