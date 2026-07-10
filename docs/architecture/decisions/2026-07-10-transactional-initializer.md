# 2026-07-10: Transactional Initializer Plan and Apply

## Status

Accepted.

## Context

The initializer treated any existing destination as a global error unless
`--force` was supplied. Dry-run inherited that conflict gate, so it could not
preview a realistic application. Force then overwrote every differing file
without merge, backup, or rollback, including user-authored guidance and client
configuration.

## Decision

Preflight every selected starter into one of five explicit actions before any
mutation:

- `ADD` for a missing destination;
- `UNCHANGED` for byte-current or already-satisfied content;
- `MERGE` for supported dependency, package metadata, Codex config, and Claude
  settings changes;
- `CONFLICT` for an existing file without a lossless merge; and
- `SKIP` for user-owned guidance such as `AGENTS.md`.

Dry-run always prints the complete plan and returns without requiring force or
creating directories, backups, or generated files. Normal apply refuses the
entire plan when any conflict exists. Force selects conflicts for explicit
replacement but never converts `SKIP` into an overwrite.

Apply backs up every changed existing destination under the ignored,
collision-proof `.agent-maintainer/backups/init/<transaction>/` root. It writes
a restore/remove manifest, uses same-directory atomic replacements, and restores
or removes all earlier destinations when a later write fails. A second apply of
the same desired state selects no writes and creates no transaction.

Planning and mutation are separate modules in the scaffold domain. Their edges
are recorded in `src/agent_maintainer/core/tach.domain.toml`.

## Consequences

Existing applications can review adoption without choosing between no output
and destructive force. Supported user content survives merges, guidance remains
owned by the user, and unsupported conflicts are visible before apply.

The initializer deliberately does not attempt semantic YAML or workflow merges.
Those remain explicit conflicts because silently rewriting comments, anchors, or
CI behavior would be less safe than requiring review.

## Alternatives Considered

- Perform a best-effort write for every non-conflicting file. Rejected because
  a plan with one unresolved conflict should not partially onboard a repository.
- Treat every text file as appendable. Rejected because duplicate or reordered
  configuration can change behavior.
- Let force overwrite `AGENTS.md`. Rejected because force resolves generated
  conflicts; it does not transfer ownership of user guidance.
- Reuse hook-specific transaction types directly. Rejected to keep initializer
  planning independent from one client integration.

## Verification

Tests cover all five preview classifications, dry-run byte preservation,
whole-plan conflict refusal, merge-aware forced apply, user guidance
preservation, conflict backups, package metadata preservation, interrupted-write
rollback, and second-run byte/transaction equality.
