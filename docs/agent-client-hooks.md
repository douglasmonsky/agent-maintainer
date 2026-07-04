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

Repo-local wrappers use the checked-out source tree:

```bash
python3 -m agent_maintainer verify --profile fast
python3 -m agent_maintainer verify --profile precommit
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
