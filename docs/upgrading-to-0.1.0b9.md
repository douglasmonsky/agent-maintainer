<!-- docsync:object docs.upgrade_0_1_0b9.overview -->
# Upgrading from 0.1.0b8 to 0.1.0b9

`0.1.0b9` is currently unpublished. Use this guide only to evaluate a trusted
candidate checkout or locally built distribution; keep `0.1.0b8` pinned for
normal package-index installation until the release index moves.

## Before You Start

1. Commit or otherwise preserve the application repository's current state.
2. Record existing agent-client and repository-tool configuration.
3. Keep the published beta available for rollback:

   ```bash
   python -m pip install "agent-maintainer[core]==0.1.0b8"
   ```

4. Install the candidate from a trusted clean checkout:

   ```bash
   python -m pip install -e ".[core]"
   agent-maintainer doctor
   ```

## Review Candidate Scope

`0.1.0b9` adds diff-aware verification planning and declarative path-risk
policy. Existing verification commands and profiles keep their prior behavior;
the planner is additive and does not dynamically skip configured gates.

- Run the advisory planner against a trusted base ref:

  ```bash
  agent-maintainer verify-plan --base-ref origin/main
  ```

- Use `--json` for deterministic `schema_version = 1` output and `--staged` to
  plan the exact staged diff.
- Add `.agent-maintainer/path-risk.toml` only after reviewing the versioned
  policy contract. Unknown fields, unsafe paths, malformed globs, unknown
  profiles, and ambiguous check names fail closed.
- Add `--enforce` when missing required evidence should return exit status `1`.
  Invalid policy, configuration, or Git input returns `2`.
- Treat recommended commands as an explanation of required verification, not
  as permission to omit existing repository or CI gates.

There are no breaking changes to existing CLI, configuration, or verifier
execution contracts. Repositories without path-risk policy remain advisory and
do not gain the optional policy gate.

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
python -m pip install --force-reinstall "agent-maintainer[core]==0.1.0b8"
```

Do not copy candidate-generated files over the restored state. If a mutation
was interrupted, inspect its ignored backup record before retrying or removing
anything manually.
<!-- docsync:object.end docs.upgrade_0_1_0b9.overview -->
