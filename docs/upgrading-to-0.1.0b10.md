<!-- docsync:object docs.upgrade_0_1_0b10.overview -->
# Upgrading from 0.1.0b9 to 0.1.0b10

`0.1.0b10` is published on PyPI. Use this guide to adopt opt-in semantic
contract ratchets in an existing repository.

## Before You Start

1. Commit or otherwise preserve the application repository's current state.
2. Record existing agent-client and repository-tool configuration.
3. Keep the prior published beta available for rollback:

   ```bash
   python -m pip install "agent-maintainer[core]==0.1.0b9"
   ```

4. Install the published release:

   ```bash
   python -m pip install --upgrade "agent-maintainer[core]==0.1.0b10"
   agent-maintainer doctor
   ```

## Review Release Scope

`0.1.0b10` adds opt-in semantic contract ratchets. Existing repositories are
unchanged unless they add `.agent-maintainer/contracts.toml` and a generated
`.agent-maintainer/contracts-baseline.json`. Repositories that opt in should
review declared owners, stability, revisions, migration paths, and exact
review-decision fingerprints before enabling the verifier gate.

Pre-commit verification reads contract inputs from the Git index. Keep policy,
baseline, package-version, source, and migration evidence staged together for
intentional contract changes; unstaged worktree content is deliberately ignored
by that gate.

Preview every repository mutation before applying it:

```bash
agent-maintainer init --dry-run --track core --preset existing-app
agent-maintainer install --dry-run
```

## Complete The Upgrade

Run the profiles appropriate to the repository and inspect the final diff:

```bash
agent-maintainer doctor
agent-maintainer verify --profile precommit
agent-maintainer verify --profile full
agent-maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
agent-maintainer verify --profile security
```

## Rollback

If the new behavior is unsuitable, restore the preserved repository state
and reinstall the prior published beta:

```bash
python -m pip install --force-reinstall "agent-maintainer[core]==0.1.0b9"
```

Do not copy generated files over the restored state. If a mutation was
interrupted, inspect its ignored backup record before retrying or removing
anything manually.
<!-- docsync:object.end docs.upgrade_0_1_0b10.overview -->
