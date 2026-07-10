<!-- docsync:object docs.agent_client_hooks.overview -->

# Agent Client Hooks

Agent Maintainer can install managed hooks for supported coding-agent clients.
The hooks run local verification and feed failures back into the active agent
turn.

Supported clients:

| Client | Config | Hook wrappers |
|---|---|---|
| Codex | `.codex/config.toml` | `.codex/hooks/post_edit_fast_gate.py`, `.codex/hooks/post_pr_wait.py`, `.codex/hooks/stop_full_verify.py`, `.codex/hooks/hook_audit.py` |
| Claude Code | `.claude/settings.json` | `.claude/hooks/post_tool_use.py`, `.claude/hooks/post_pr_wait.py`, `.claude/hooks/stop.py`, `.claude/hooks/subagent_stop.py` |

One managed-file manifest owns each path, renderer, scope, merge strategy,
ownership marker, status policy, scaffold inclusion, and uninstall behavior.
Client adapters select from that manifest. The shared hook manager owns
permission prompts, dry-run behavior, backups, and file writes.

Install repo-local hook files:

```bash
python3 -m agent_maintainer hooks install all
```

Inspect hook status:

```bash
python3 -m agent_maintainer hooks status all
```

Update installed hooks through the same merge and backup contract:

```bash
python3 -m agent_maintainer hooks update all --dry-run
python3 -m agent_maintainer hooks update all
```

Remove only manifest-owned entries and scripts:

```bash
python3 -m agent_maintainer hooks uninstall all --dry-run
python3 -m agent_maintainer hooks uninstall all
```

Uninstall preserves unrelated Codex and Claude configuration, including a
third-party command co-located inside a managed Claude matcher. Current managed
scripts are removed directly. A stale script must retain its ownership marker
and requires `--force`; an unowned file is refused even with force.

Preview changes before writing files:

```bash
python3 -m agent_maintainer hooks install all --dry-run
```

Claude Code can opt into asynchronous rewake for slow stop-time validation while
keeping `PostToolUse` fast checks synchronous:

```bash
python3 -m agent_maintainer hooks install claude-code --dry-run --async-rewake-stop
python3 -m agent_maintainer hooks install claude-code --async-rewake-stop
```

In this mode, only Claude Code `Stop` and `SubagentStop` entries receive
`async: true` and `asyncRewake: true`. Their generated commands/wrappers also
pass Agent Maintainer runtime async-rewake mode, so pending or failed
verification emits the compact wait/repair context on stderr and exits `2` for
Claude Code rewake.

Install only one client:

```bash
python3 -m agent_maintainer hooks install codex
python3 -m agent_maintainer hooks install claude-code
```

User-level installs are available for people who want hooks outside one repo.
They require explicit confirmation because they write under the home directory:

```bash
python3 -m agent_maintainer hooks install claude-code --scope user
```

Use `--yes` only in deliberate automation:

```bash
python3 -m agent_maintainer hooks install claude-code --scope user --yes
```

Changed existing files are always backed up, including when `--force` resolves
an invalid managed config or a stale owned script. Repository recovery data
lives under Git-private
`.git/agent-maintainer/backups/hooks/<transaction>/` storage. User-scope and
non-Git operations fall back to `.agent-maintainer/backups/hooks/` under their
ownership root. Each transaction includes a `rollback.json` restore/remove
manifest. Writes and removals are applied atomically as one transaction and
earlier destinations are restored if a later operation fails. Dry-run mode
never prompts for user-level permission, writes files, removes files, or creates
backups. A second current install or update is a byte-for-byte no-op and creates
no new transaction.

User-level hooks are repo opt-in. When a global hook fires outside a Git
repository, or inside a repository without `[tool.agent_maintainer]` in
`pyproject.toml`, Agent Maintainer exits successfully without running
verification and without writing `.verify-logs`.

## Hook Behavior

`PostToolUse` hooks run the `fast` profile after edits. `Stop` and
`SubagentStop` hooks run the `precommit` profile before the agent finishes.

When those hooks are trusted and pass for the final repository state, agents
should not start a duplicate manual `precommit` run. Manual `precommit` is for
hook-unavailable sessions, bypassed hooks, reproducing a hook failure, or changed
repo state after the hook pass.

Hooks check verifier readiness before starting new work. If the same repository
state already has a verifier running, the hook returns a compact wait pointer
instead of launching a duplicate process. If the same-state verifier already
completed, the hook reuses that pass or failure result. If the working tree,
index, configured profile, base, or compare state changed, the hook starts fresh
verification.

A Bash `gh pr create` `PostToolUse` hook detects created PR URLs before review
or merge. Claude Code uses async rewake handoff. Codex registers a
durable background wait by default, starts a silent watcher, and emits one
compact manual-resume plus wait-scoped heartbeat prompt. Direct Codex
`wait github-pr`, `wait github-run`, and `wait verifier` commands also convert
to background waits unless `AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1` is set. Direct Codex
verifier commands such as `python -m agent_maintainer verify --profile ci` and
repo `just v` / `just vc` wrappers start an async verifier and emit the same
background wait heartbeat handoff by default.
The heartbeat prompt should run
`python -m agent_maintainer wait sweep --one <wait-id> --root <repo>`, stay
silent while that wait is pending, and print its terminal resume capsule once.
Structured heartbeat requests include `on_pending: silent`, `on_terminal:
resume_and_review`, and `merge_policy: merge_only_if_satisfactory`; stale ready
records can be expired with `python -m agent_maintainer wait cleanup --root <repo>`.
Terminal-only local polling is preferred for Codex waits. Launchd failure is
reported instead of silently downgrading to a detached `popen` watcher. Automatic
visible Codex thread rewake is not treated as proven today; app-server turn
acceptance keeps the wait ready for manual `wait resume <id>` recovery. Heartbeat
fallback still wakes a model each interval, so use it only when explicit manual
monitoring is acceptable.
Repo-local wrappers use the checked-out source tree:

```bash
just verify-fast
just verify-precommit
```

User-level hooks call the installed console command:

```bash
agent-maintainer hooks run --platform claude-code --event PostToolUse --profile fast
```

## Trust Review

Review hook files before approving them in any agent client. Treat trust as tied
to the exact hook configuration, hook script contents, source path, and content
hash. Re-review hooks after changing:

- `.codex/config.toml`
- `.codex/hooks/post_edit_fast_gate.py`
- `.codex/hooks/post_pr_wait.py`
- `.codex/hooks/stop_full_verify.py`
- `.codex/hooks/hook_audit.py`
- `.claude/settings.json`
- `.claude/hooks/post_tool_use.py`
- `.claude/hooks/post_pr_wait.py`
- `.claude/hooks/stop.py`
- `.claude/hooks/subagent_stop.py`
- the command each hook runs
- the repository path copied into hook configuration

Agent Maintainer hook commands remain local. They do not transmit prompt text,
tool payloads, verifier output, secrets, private data, or student data.

## Audit Trail

Hook wrappers append compact local records to:

```text
.verify-logs/hooks.jsonl
```

Audit records include platform, hook event, verifier profile, command, exit
code, status, timestamps, and duration. They intentionally do not include hook
stdin, prompts, tool payloads, verifier stdout, or verifier stderr.

Run setup diagnostics when hooks are installed but not behaving as expected:

```bash
python3 -m agent_maintainer doctor
```
<!-- docsync:object.end docs.agent_client_hooks.overview -->
