<!-- docsync:object docs.upgrade_0_1_0b12.overview -->
# Upgrading from 0.1.0b10 to 0.1.0b12

`0.1.0b12` is published on PyPI with immutable evidence in the
[release record](releases/0.1.0b12.md). Use this guide to adopt the experimental,
disabled-by-default C/C++ foundation while keeping `0.1.0b10` available for
rollback.

## Before You Start

1. Commit or otherwise preserve the application repository's current state.
2. Record existing agent-client and repository-tool configuration.
3. Keep the published beta available for rollback:

   ```bash
   python -m pip install "agent-maintainer[core]==0.1.0b10"
   ```

4. Install the published release and inspect repository health:

   ```bash
   python -m pip install "agent-maintainer[core]==0.1.0b12"
   agent-maintainer doctor
   ```

## Review Release Scope

The experimental C/C++ provider is disabled by default. To evaluate its static
Phase 187 surface, add reviewed repository-owned command arrays and enable it:

```toml
[tool.agent_maintainer.cpp]
enabled = true
cmake_root = "."
build_command = ["cmake", "--build", "--preset", "ci"]
test_command = ["ctest", "--preset", "ci"]
```

Run `agent-maintainer doctor` and inspect the C/C++ rows. Use
`python -m agent_maintainer assess reviewability` to inspect advisory
classification and suppression evidence for changed C/C++ files. Phase 187
does not execute the configured commands.

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

The normal verifier profiles do not schedule C/C++ commands in Phase 187.

## Rollback

If the new behavior is unsuitable, restore the preserved repository state
and reinstall the published beta:

```bash
python -m pip install --force-reinstall "agent-maintainer[core]==0.1.0b10"
```

Do not copy generated files from the failed upgrade over the restored state. If a mutation
was interrupted, inspect its ignored backup record before retrying or removing
anything manually.
<!-- docsync:object.end docs.upgrade_0_1_0b12.overview -->
