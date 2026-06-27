# Architecture Decision: Add Fresh-Strict Example Tach Policy

Status: accepted

## What Changed?

The `examples/fresh-strict` starter project now includes its own `tach.toml`.
The example config uses `root_module = "forbid"` and `exact = true` for the
toy `fresh_strict_example` package.

## Why Necessary?

The fresh-strict example is intended to show new repositories how to adopt a
strict architecture contract from the first commit. Including the Tach policy in
the example makes the documented adoption path executable and test-backed
instead of prose-only.

## Why Is This Not Just Architecture Drift?

This change does not relax the repository's production Tach policy. It adds an
isolated example policy under `examples/` so package-first adopters can inspect
and run a minimal strict configuration. The example uses stricter root handling,
not a permissive fallback.

## Alternatives Considered

1. Document the Tach snippet only in Markdown.
2. Reuse the repository root `tach.toml` for examples.
3. Add the executable example with its own local Tach policy.

The executable example was chosen because it can be validated by tests and keeps
the example package independent of this repository's larger module graph.

## Boundary Impact

The example Tach policy applies only to `examples/fresh-strict`. It does not
change allowed imports for `agent_maintainer`, `archguard`, or Codex hook
modules.

## What Remains Forbidden?

Do not weaken root `tach.toml`, add broad module dependencies, or relax
`root_module = "forbid"` to make unrelated architecture changes pass. Example
policies should stay narrow, runnable, and representative of the mode they
document.

## Review Or Expiration Condition

Revisit this example after beta users try `fresh-strict` on real repositories.
If the example no longer matches recommended Tach adoption, update the example
and this decision note together.
