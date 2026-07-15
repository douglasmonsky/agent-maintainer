<!-- docsync:object docs.upgrade_0_1_0b7.overview -->
# Upgrading from 0.1.0b6 to 0.1.0b7

`0.1.0b7` is currently unpublished. Use this guide only to evaluate a trusted
candidate checkout or locally built distribution; keep `0.1.0b6` pinned for
normal package-index installation until the release index moves.

## Before You Start

1. Commit or otherwise preserve the application repository's current state.
2. Record existing Codex and Claude hook configuration owned by other tools.
3. Keep the published beta available for rollback:

   ```bash
   python -m pip install "agent-maintainer[core]==0.1.0b6"
   ```

4. Install the candidate from a trusted clean checkout:

   ```bash
   python -m pip install -e ".[core]"
   agent-maintainer doctor
   ```

## Preview Repository Mutations

Preview initialization and hook installation before applying either operation:

```bash
agent-maintainer init --dry-run --track core --preset existing-app
agent-maintainer install --dry-run
```

Review every add, merge, conflict, skip, and replacement. Existing third-party
Codex or Claude commands should remain present. Resolve conflicts explicitly;
do not use force as a substitute for reviewing ownership.

## Check Behavior Changes

- Commits use fast staged policy plus affected tests; pushes require a clean
  checkout and run the complete profile against the exact outgoing Git range.
- CI and release jobs may run verifier groups concurrently, but protected
  aggregation still rejects incomplete, failed, or mismatched evidence.
- Worktree doctor output distinguishes missing hooks, stale run artifacts, and
  safe cleanup actions without deleting unknown files.
- Public stability labels identify which commands are core, optional, or
  experimental.
- Import canonical run-artifact behavior from `agent_run_artifacts`; the
  repository-unused `agent_maintainer.verify` forwarding modules are gone.

## Complete The Evaluation

Run the profiles appropriate to the repository and inspect the final diff:

```bash
agent-maintainer doctor
agent-maintainer verify --profile precommit
agent-maintainer verify --profile full
agent-maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
agent-maintainer verify --profile security
```

Existing applications should also confirm that install, update, status, and
uninstall preserve user-owned client hooks and leave the worktree clean after a
second identical run.

## Rollback

If candidate behavior is unsuitable, restore the preserved repository state
and reinstall the published beta:

```bash
python -m pip install --force-reinstall "agent-maintainer[core]==0.1.0b6"
```

Do not copy candidate-generated files over the restored state. If a mutation
was interrupted, inspect its ignored backup record before retrying or removing
anything manually.
<!-- docsync:object.end docs.upgrade_0_1_0b7.overview -->
