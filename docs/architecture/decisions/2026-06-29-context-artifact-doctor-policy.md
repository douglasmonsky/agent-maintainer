# Context Artifact Doctor Policy Module

## Status

Accepted.

## Context

Phase 18 adds a doctor check for workflow artifact uploads that could publish
local-only context packs. The check needs to inspect GitHub Actions workflow
text and report unsafe `.verify-logs/` uploads when context packs are configured
as source-bearing local artifacts.

## Decision

Add `agent_maintainer.doctor.support.context_artifacts` as a doctor support
module and assign it explicitly in `tach.toml`.

The module stays in the doctor support area because it only evaluates setup
policy and returns `DoctorResult` values. It does not run verification checks or
write context packs.

## Alternatives Considered

- Put the logic in `doctor.support.policy`: rejected because that module already
  owns unrelated Pyright, pip-audit, and secret-scanning policy checks.
- Put the logic in `context`: rejected because this is a doctor setup-policy
  check, not context pack generation.

## Boundaries

The module may depend on configuration and doctor result models. It must not
depend on verifier execution, hook runtime, or context pack generation.
