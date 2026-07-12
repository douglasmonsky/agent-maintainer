# Wait Command Rendering Boundary

## Status

Accepted.

## Decision

`agent_waits.command_rendering` owns POSIX shell rendering for durable wait
resume and sweep commands. It shell-quotes executable, wait identifier, and
root tokens, and preserves `PYTHONPATH` by resolving relative entries against
the durable wait root. It renders text only; it never executes commands,
inspects repository content, polls waits, or owns registry state.

`registry` delegates default resume rendering and `broker` delegates heartbeat
sweep and root-appending rendering. Custom resume instructions remain caller
owned and retain their existing structured request behavior.

## Alternatives Considered

- Leave rendering split between registry and broker. Rejected because source
  checkout import paths and shell quoting could drift.
- Put shell execution in the leaf. Rejected because command rendering must
  remain deterministic and side-effect free.
- Add a platform-specific command layer. Rejected because current Codex waits
  use the existing POSIX shell policy.
