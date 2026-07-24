# Symphony Pilot Operations

## Start and Stop

Prerequisites:

- `~/.codex/bin/symphony` points to the approved pinned release;
- `~/.codex-symphony/config.toml` exists and
  `~/.codex-symphony/auth.json` resolves to the existing ChatGPT login;
- `codex login status` and `gh auth status` succeed;
- port `4000` is available on loopback.

Start:

```bash
scripts/start-symphony
```

Stop:

```bash
scripts/stop-symphony
```

Inspect:

```bash
scripts/status-symphony
open http://127.0.0.1:4000/
```

The wrappers use an ephemeral per-user `launchctl` job. They do not install a
system daemon or require `sudo`. Runtime state and logs live under
`~/.codex/symphony/agent-maintainer`. Issue workspaces default to
`~/Developer/Codex/symphony-workspaces/agent-maintainer`.

The start script reads the existing GitHub CLI credential into the Symphony host
environment without printing it. Symphony removes `GITHUB_TOKEN` from the Codex
child environment before the App Server starts.

The official `v0.0.2` binary also requires the explicit
`--i-understand-that-this-will-be-running-without-the-usual-guardrails`
engineering-preview acknowledgement. The wrapper supplies it only alongside the
pilot controls documented in the security model.

## Create an Eligible Issue

Use the **Agent-ready task** issue form. Confirm every required section is
complete and apply `agent-ready` only after product, architecture, dependency,
permission, and verification decisions are resolved.

Lifecycle:

```text
open + agent-ready
  -> open + agent-ready + agent-running
  -> open + human-review
  -> closed
```

Blocked:

```text
open + agent-ready + agent-running
  -> open + agent-blocked
  -> human correction
  -> open + agent-ready
```

Only `agent-ready` is dispatchable. Do not use it as a general priority label.

## Monitor a Task

The stock dashboard provides issue state, session, runtime, turns, last Codex
event/message, tokens, retry attempts, and blocked errors. The issue detail JSON
provides the workspace path:

```bash
curl -fsS http://127.0.0.1:4000/api/v1/GH-123
```

`scripts/status-symphony` supplements the dashboard with:

- issue and Symphony state;
- workspace and branch;
- dirty-file count;
- recent commit;
- persisted Agent Maintainer verification status;
- pull-request URL;
- blocked reason and last activity.

It reads structured Symphony JSON, Git state, `.verify-logs/manifest.json`, and
GitHub metadata. It does not scrape terminal logs.

## Intervene from Desktop

1. Remove `agent-ready` to prevent a new claim.
2. Find the workspace with `scripts/status-symphony` or the issue detail JSON.
3. Open it as a new Desktop context:

   ```bash
   codex app "/absolute/workspace/path"
   ```

4. Inspect the worktree, current branch, workpad, diff, and verification logs.
5. Continue interactively if safe.
6. Requeue by removing `agent-blocked` and restoring `agent-ready`.

Removing `agent-ready` is the pilot pause control. To cancel, remove
`agent-ready` and `agent-running`, add `agent-blocked` with a reason, and stop
the service if the active worker does not reconcile promptly. Symphony `v0.0.2`
does not provide a dedicated pause/cancel dashboard button.

## Review and Complete

For `human-review`:

1. Review the pull-request diff and verification evidence.
2. Wait for required GitHub checks and resolve conversations.
3. Request rework by removing `human-review` and adding `agent-ready`, with
   precise issue or PR feedback.
4. Merge manually when satisfied.
5. Close the issue if the merge did not close it automatically.

The pilot never auto-merges and never changes branch protection.

## Workspace Cleanup

Keep workspaces through human review. After the PR is merged or abandoned,
confirm the workspace path and branch are no longer needed. Cleanup is manual
and requires deliberate authorization; the pilot scripts do not recursively
delete workspaces.

## Increase Concurrency

After at least two successful issue-to-PR runs and one clean blocked/requeue
cycle:

1. Confirm CPU, disk, network, GitHub rate limits, and verification duration are
   acceptable.
2. Confirm issues do not overlap in files or architecture boundaries.
3. Change `agent.max_concurrent_agents` in `WORKFLOW.md` from `1` to `2`.
4. Run two synthetic, non-overlapping tasks and inspect the dashboard and status
   command.
5. Revert to `1` on workspace collision, resource pressure, auth contention, or
   ambiguous dashboard state.

Do not increase concurrency automatically.

## Enable an MCP Safely

Keep all optional MCPs disabled during the pilot. For Serena or GitNexus:

1. Test in a disposable isolated clone under the Symphony workspace root.
2. Prove the tool derives the active repository dynamically and cannot mutate
   or disclose another checkout.
3. Prove startup is noninteractive and no browser login is required.
4. Bound or recreate indexes per workspace.
5. Enable only that MCP in `~/.codex-symphony/config.toml`.
6. Run a labeled test issue whose acceptance criteria require the tool.
7. Record the result in the validation report.

## Upgrade Symphony

Never replace the stable binary in place.

1. Read the official release notes, `SPEC.md`, Elixir `README.md`, config schema,
   GitHub adapter, dashboard presenter, and migration notes between the pinned
   revision and candidate tag.
2. Download the platform binary and matching `.sha256` from the official
   release.
3. Verify the checksum and install as
   `~/.codex/bin/symphony-<version>`.
4. Ensure no issue has `agent-ready`, then stop the current service.
5. Start the candidate without moving the stable link:

   ```bash
   SYMPHONY_BIN="$HOME/.codex/bin/symphony-<version>" \
     scripts/start-symphony
   ```

6. Verify config loading, loopback bind, JSON schema, dashboard fields, GitHub
   polling, a blocked dry run, and one low-risk issue-to-PR run.
7. Stop the candidate. Only after successful comparison, point
   `~/.codex/bin/symphony` to the new version.
8. Keep the prior versioned binary for rollback.

If the schema or behavior changes, update `WORKFLOW.md`, scripts, docs, and the
validation report in one reviewed pull request.
