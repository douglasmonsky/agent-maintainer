# 2026-07-10: Safe Hook Mutation

## Status

Accepted.

## Context

Setup commands previously discarded their arguments, bootstrap implicitly
installed hooks, Claude merge replaced complete event arrays, `--force`
suppressed backups, and second-resolution backup names could collide. Sequential
direct writes also allowed a late failure to leave a partially updated hook set.

## Decision

Parse `bootstrap` and `install` arguments before behavior in
`agent_maintainer.core.setup_cli`. Help and invalid arguments terminate in the
parser. Both commands accept a side-effect-free `--dry-run` and explicit target.
Bootstrap owns dependency setup only; hook and pre-commit installation requires
the explicit `install` or `hooks install` command.

Claude settings merge removes only entries whose command carries a stable Agent
Maintainer console-command or managed-wrapper identity. Unrelated hook entries,
event arrays, fields, and ordering are preserved.

Hook installation renders and validates every plan before the first mutation.
Changed existing files are always backed up, including with `--force`, under a
collision-proof transaction directory at
`.agent-maintainer/backups/hooks/<transaction>/`. The directory is ignored by
Git. Each transaction records restore/remove actions in `rollback.json`, writes
destinations with same-directory atomic replacement, and restores earlier
destinations if a later write fails.

`--force` is limited to resolving a known invalid managed configuration by
replacing it after backup. It does not disable merge, backup, preview, or
rollback promises.

## Consequences

Repeated installation of current files is a byte-for-byte no-op and creates no
new transaction. Users can review plans without prompts, package installation,
pre-commit execution, hook writes, or backup creation. Recovery metadata stays
local and ignored while preserving original file modes and contents.

The new module edges are recorded in
`src/agent_maintainer/core/tach.domain.toml`,
`src/agent_maintainer/hooks/tach.domain.toml`, and
`src/agent_client_hooks/tach.domain.toml`.

## Alternatives Considered

- Keep adjacent timestamped backup files. Rejected because they dirty the
  repository and can collide.
- Treat `--force` as permission to skip backup. Rejected because force resolves
  a conflict; it does not waive recoverability.
- Append all managed Claude entries. Rejected because stale managed entries
  would duplicate while unrelated hooks still need stable ordering.
- Write files sequentially and rely on backups for manual recovery. Rejected
  because the command can automatically restore a coherent pre-run state.

## Verification

Tests cover help and typo behavior through the real package entrypoint, dry-run
side effects, third-party hooks in every managed Claude event, repeated merge
idempotency, forced and ordinary backups, rapid collision-proof transactions,
second-run byte equality, rollback after an interrupted later write, and
recovery-manifest contents.
