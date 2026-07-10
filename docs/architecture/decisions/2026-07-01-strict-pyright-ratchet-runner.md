# Strict Pyright Ratchet Runner Boundary

## Decision

`agent_maintainer.runners.pyright_strict` is a separate runner module from
`agent_maintainer.runners.pyright`.

The strict runner may depend on the normal Pyright runner for shared generated
config helpers and on a dependency-free baseline module, but the normal
Pyright runner must not depend on either strict-ratchet module.

The committed baseline uses schema version 2. It records a positive count for
each repository-relative file/rule pair, the exact Pyright version, and a
SHA-256 fingerprint of the normalized generated strict scope. A run passes only
when the tool and scope identities match and every current pair is at or below
its own allowance. Resolved pairs may disappear; a new pair starts with an
allowance of zero. Aggregate totals and per-rule counts are review summaries,
not acceptance criteria, and must agree with the canonical pairs.

The runner writes an ignored candidate baseline for intentional review. It
never promotes that candidate automatically. A nonzero
`pyright_strict_max_errors` fails closed while the v2 ratchet is enabled because
a global budget would permit debt to move between files or rules.

## Rationale

Normal Pyright remains the zero-error local gate. Strict Pyright is a separate
manual ratchet that compares current strict diagnostics against a committed
baseline. File/rule pairs prevent a lower total from hiding error substitution.
Tool and scope identity prevent an upgrade or narrowed include set from being
misreported as typing improvement. Keeping the runner separate prevents these
baseline policies from complicating the default Pyright path.

## Alternatives Considered

Extending the normal Pyright runner with strict-ratchet flags was rejected
because it would mix two policies: "current configured mode must pass" and
"strict mode may have a ratcheted baseline." Separate modules keep those
policies easier to test and reason about.

An aggregate error-count baseline was replaced because one repaired diagnostic
could otherwise pay for an unrelated new diagnostic. Per-rule and per-file
totals were also insufficient independently: debt could still move between a
file and rule while both aggregate views stayed under budget.

## Still Forbidden

The strict runner should not import verifier orchestration or reporting code.
It should remain a small tool runner that reads config, invokes Pyright, writes
artifacts, and exits with a compact ratchet result. Baseline version, summaries,
paths, counts, tool identity, scope identity, and diagnostic/summary agreement
must fail closed when malformed or inconsistent.
