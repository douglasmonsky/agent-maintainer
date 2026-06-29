# Context Artifact Doctor Policy Module

## Status

Accepted.

## Context

Phase 18 added doctor checks for workflow artifact uploads that could publish
local-only context packs. Phase 27 extends doctor health reporting across
context config, ratchets, change plans, compression, and test-intelligence
artifacts. These checks inspect repository setup and configuration; they should
not execute verifier profiles or generate context packs.

## Decision

Add `agent_maintainer.doctor.support.context_artifacts` and
`agent_maintainer.doctor.support.context_health` as doctor support modules and
assign them explicitly in `tach.toml`.

The modules stay in the doctor support area and only evaluate setup policy into
`DoctorResult` values. They may read configuration, safe metadata files, and
workflow text, but they do not run verification checks or write context packs.

## Alternatives Considered

- Put logic in `doctor.support.policy`: rejected because that module already
  owns unrelated Pyright, pip-audit, and secret-scanning policy checks.
- Put logic in `context`: rejected because these are doctor setup-policy checks,
  not context pack generation.
- Put Phase 27 rows directly in `doctor.cli`: rejected because row-specific
  policy logic would make CLI orchestration harder to scan and test.

## Boundaries

Doctor support modules may depend on configuration, doctor result models, and
safe read-only project metadata. They must not depend on verifier execution,
hook runtime, or context pack generation.
