# Strict Pyright Ratchet Runner Boundary

## Decision

`agent_maintainer.runners.pyright_strict` is a separate runner module from
`agent_maintainer.runners.pyright`.

The strict runner may depend on the normal Pyright runner for shared generated
config helpers, but the normal Pyright runner must not depend on the strict
ratchet runner.

## Rationale

Normal Pyright remains the zero-error local gate. Strict Pyright is a separate
manual ratchet that compares current strict diagnostics against a committed
baseline. Keeping the runner separate prevents strict-mode baseline logic from
complicating the default Pyright path.

## Alternatives Considered

Extending the normal Pyright runner with strict-ratchet flags was rejected
because it would mix two policies: "current configured mode must pass" and
"strict mode may have a ratcheted baseline." Separate modules keep those
policies easier to test and reason about.

## Still Forbidden

The strict runner should not import verifier orchestration or reporting code.
It should remain a small tool runner that reads config, invokes Pyright, writes
artifacts, and exits with a compact ratchet result.
