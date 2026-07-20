<!-- docsync:object docs.upgrade_0_1_0b14.overview -->
# Upgrading from 0.1.0b12 to 0.1.0b14

`0.1.0b14` is currently unpublished. Use this guide only to evaluate a
trusted candidate checkout or locally built distribution; keep `0.1.0b12`
pinned for normal package-index installation until the release index moves.

## Before You Start

1. Commit or otherwise preserve the application repository's current state.
2. Record existing agent-client and repository-tool configuration.
3. Keep the published beta available for rollback:

   ```bash
   python -m pip install "agent-maintainer[core]==0.1.0b12"
   ```

4. Install the candidate from a trusted clean checkout:

   ```bash
   python -m pip install -e ".[core]"
   agent-maintainer doctor
   ```

## Review Candidate Scope

The TypeScript package-manager audit surface is explicit and advisory. Review
the configured manager, command, workspace, and profile before evaluation. The
parser accepts bounded JSON/NDJSON evidence and does not infer package-manager
behavior or enable a blocking gate. Yarn and Bun remain fixture-only.

Preview every repository mutation before applying it:

```bash
agent-maintainer init --dry-run --track core --preset existing-app
agent-maintainer install --dry-run
```

## Complete The Evaluation

Run the profiles appropriate to the repository and inspect the final diff:

```bash
agent-maintainer doctor
agent-maintainer verify --profile precommit
agent-maintainer verify --profile full
agent-maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
agent-maintainer verify --profile security
```

## Rollback

If candidate behavior is unsuitable, restore the preserved repository state
and reinstall the published beta:

```bash
python -m pip install --force-reinstall "agent-maintainer[core]==0.1.0b12"
```

Do not copy candidate-generated files over the restored state. If a mutation
was interrupted, inspect its ignored backup record before retrying or removing
anything manually.
<!-- docsync:object.end docs.upgrade_0_1_0b14.overview -->
