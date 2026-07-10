# 2026-07-10: Managed Hook File Manifest

## Status

Accepted.

## Context

Agent-client hook paths were repeated across adapters, installation plans,
initializer templates, status checks, uninstall plans, and documentation. The
copies had already diverged: new repositories configured PR-wait wrappers that
the initializer omitted, Codex installation wrote an audit shim that status and
uninstall ignored, and user-scope status expected repo-only scripts.

Existence-only status also could not distinguish a current generated wrapper
from a stale checked-in copy.

## Decision

Make `agent_client_hooks.manifest` the authoritative managed-file inventory.
Each record declares its client, relative path, renderer, supported scopes,
merge strategy, ownership marker, status policy, scaffold inclusion, and
uninstall behavior.

Client adapters select install and uninstall plans from the manifest. Scaffold
templates render the same selected records. Currentness checks live in
`agent_client_hooks.status`, accept the supported default and Claude async-stop
variants, and treat user-scope wrappers as intentionally unmanaged. Public hook
inventory tests require every manifest path to remain documented.

The dependency changes are explicit in:

- `src/agent_client_hooks/tach.domain.toml`, where adapters and status depend on
  the manifest; and
- `src/agent_maintainer/core/tach.domain.toml`, where scaffold templates depend
  on the manifest instead of directly enumerating hook templates.

## Consequences

Adding or removing a managed hook file now requires one lifecycle record.
Installer, scaffold, status, uninstall, checked-in renderer-currentness, and
documentation tests fail together when that record is incomplete or stale.

Configuration merge algorithms and transactional writes remain separate from
the inventory. The manifest declares which strategy applies without owning
filesystem mutation.

## Alternatives Considered

- Keep adapter path tuples and test them against scaffold tuples. Rejected
  because it preserves two sources of truth and does not cover documentation or
  uninstall scope.
- Put the manifest in `agent_maintainer.hooks`. Rejected because the extracted
  `agent_client_hooks` package already owns client-specific templates and
  adapters and must remain independent of the product package.
- Treat existence as current status. Rejected because stale generated wrappers
  were the bootstrap defect this boundary must expose.

## Verification

Tests assert unique complete records, exact install/uninstall scope selection,
complete scaffold output, byte-for-byte checked-in script currentness, complete
public inventory, and safe no-op execution of every configured generated
wrapper.
