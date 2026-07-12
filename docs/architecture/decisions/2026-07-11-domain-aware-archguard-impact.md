# Domain-aware Archguard impact analysis

## Status

Accepted.

## Context

Nested Tach domain files hold architecture ownership and dependency policy.
Read-only Archguard impact analysis must not present a permissive result when
that policy cannot be loaded.

## Decision

The shared domain loader returns parsed payloads and bounded load errors. It
flows inward to read-only impact analysis. Malformed root or domain policy
fails closed, while Tach remains the authoritative enforcement tool.

## Dependency direction

Explicit dependencies take precedence over legacy layers. This task preserves
existing layer interpretation and reports incomplete policy as unknown.

## Alternatives

Keeping malformed domains silent was rejected because it could produce broad,
misleading allowed results. Product packages do not import Archguard internals.

## Remaining constraints

The loader reports only bounded error codes, does not expose input content, and
does not replace Tach validation.
