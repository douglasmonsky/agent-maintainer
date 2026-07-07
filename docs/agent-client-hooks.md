<!-- docsync:object docs.agent_client_hooks.overview -->

# Agent Client Hooks

Agent Maintainer can install managed hooks for supported coding-agent clients.
The hooks run local verification and feed failures back into the active agent
turn.

Supported clients:

| Client | Config | Hook wrappers |
|---|---|---|
| Codex | `.codex/config.toml` | `.codex/hooks/post_edit_fast_gate.py`, `.codex/hooks/stop_full_verify.py` |
| Claude Code | `.claude/settings.json` | `.claude/hooks/post_tool_use.py`, `.claude/hooks/stop.py`, `.claude/hooks/subagent_stop.py` |

Internally, each client is represented by an `AgentClientAdapter`. Adapters own
client-specific config and hook paths. The shared hook manager still owns
permission prompts, dry-run behavior, backups, merge policy, and file writes.

Install repo-local hook files:

```bash
python3 -m agent_maintainer hooks install all
```

Inspect hook status:

```bash
python3 -m agent_maintainer hooks status all
```

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

Existing files are backed up before managed writes unless `--force` is passed.
Dry-run mode never prompts for user-level permission and never creates backups.

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
compact manual-resume plus repo-scoped heartbeat prompt. Direct Codex
`wait github-pr`, `wait github-run`, and `wait verifier` commands also convert
to background waits unless `AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1` is set. Direct Codex
verifier commands such as `python -m agent_maintainer verify --profile ci` and
repo `just v` / `just vc` wrappers start an async verifier and emit the same
background wait heartbeat handoff by default.
The heartbeat prompt should run `python -m agent_maintainer wait heartbeat --root <repo>`,
stay silent while all waits are pending, and print each terminal resume capsule
once. Structured heartbeat requests include `on_pending: silent`, `on_terminal:
resume_and_review`, and `merge_policy: merge_only_if_satisfactory`; stale ready
records can be expired with `python -m agent_maintainer wait cleanup --root <repo>`.

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
- `.codex/hooks/stop_full_verify.py`
- `.claude/settings.json`
- `.claude/hooks/post_tool_use.py`
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
