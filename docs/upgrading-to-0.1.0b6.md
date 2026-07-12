<!-- docsync:object docs.upgrade_0_1_0b6.overview -->
# Installing or Upgrading to 0.1.0b6

`0.1.0b6` is published to PyPI. Use this guide to adopt the released package
or upgrade from `0.1.0b5` while retaining a straightforward rollback path.

## Before You Start

1. Commit or otherwise preserve the application repository's current state.
2. Record existing Codex and Claude hook configuration owned by other tools.
3. Install the published release:

   ```bash
   python -m pip install "agent-maintainer[core]==0.1.0b6"
   ```

4. Confirm the installed package is healthy:

   ```bash
   agent-maintainer doctor
   ```

## Preview Repository Mutations

The initializer and hook installer now treat preview, conflicts, backups, and
rollback as product contracts. Preview before applying either operation:

```bash
agent-maintainer init --dry-run --track agent --preset existing-app
agent-maintainer install --dry-run
```

Review every add, merge, conflict, skip, and replacement. Existing third-party
Codex or Claude commands should remain present. Resolve conflicts explicitly;
do not use force as a substitute for reviewing ownership.

## Validate Configuration

The release rejects unknown keys, invalid types, contradictory settings,
unsafe paths, and invalid environment overrides before verification starts.
Run:

```bash
agent-maintainer doctor
agent-maintainer verify --profile precommit
```

If preflight fails, use the source and dotted-key diagnostic to repair the
configuration. Do not delete the setting or weaken a threshold without first
understanding the intended policy.

## Check Behavior Changes

- MCP and DocSync file operations must stay inside their approved repository
  roots and reject special, oversized, or unsafe paths.
- Detached verification and wait commands now persist lifecycle state. Use the
  printed wait or resume command rather than starting overlapping profiles.
- TypeScript/React findings remain advisory unless the repository explicitly
  owns and configures the relevant workspace commands.
- Optional MCP and experimental task-broker dependencies remain opt-in.
- The optional npm-backed hardening tools now require Node.js 22 or newer. An
  existing incompatible `engines.node` value is reported as an initializer
  conflict instead of being replaced silently.
- Release consumers verify exact artifact inventories and digests; locally
  renamed or substituted release bundles are rejected.

## Complete The Evaluation

Run the profiles appropriate to the repository and inspect the final diff:

```bash
agent-maintainer verify --profile full
agent-maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
agent-maintainer verify --profile security
```

Existing applications should also confirm that install, update, status, and
uninstall preserve user-owned client hooks and leave the worktree clean after a
second identical run.

## Rollback

If release behavior is unsuitable, restore the preserved repository state
and reinstall the prior beta:

```bash
python -m pip install --force-reinstall "agent-maintainer[core]==0.1.0b5"
```

Do not copy candidate-generated files over the restored state. If a mutation
was interrupted, inspect its ignored backup record before retrying or removing
anything manually.
<!-- docsync:object.end docs.upgrade_0_1_0b6.overview -->
