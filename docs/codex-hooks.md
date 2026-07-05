<!-- docsync:object docs.codex_hooks.overview -->
# Codex Hooks

For the full managed hook installer covering Codex and Claude Code, see
[Agent client hooks](agent-client-hooks.md).

Claude Code installations can opt into asynchronous rewake for slow
`Stop`/`SubagentStop` validation through the shared installer:
`python3 -m agent_maintainer hooks install claude-code --async-rewake-stop`.

The kit includes repo-local Codex hooks under `.codex/`:

| Hook | Purpose |
|---|---|
| `PostToolUse` | Runs the fast profile after file edits and feeds failures back into the turn. |
| `Stop` | Runs the precommit profile before the agent finishes. |

Install Codex hooks with:

```bash
python3 -m agent_maintainer hooks install codex
```

`python3 -m agent_maintainer install` also installs managed agent-client hooks
after local pre-commit setup. It does not approve Codex hooks for you.

## Trust Review

Codex hook trust is source and hash specific. Treat trust as tied to the exact hook configuration and hook script contents, not as a permanent approval for every future edit.

Re-review hooks when any of these change:

- `.codex/config.toml`
- `.codex/hooks/post_edit_fast_gate.py`
- `.codex/hooks/stop_full_verify.py`
- the command that the hook runs
- the repo path or copied hook source

The hook commands should remain repo-local and should not transmit private, student, financial, credential-bearing, or production data. This kit's hooks run local verification only.

## Expected Commands

The hook scripts invoke the canonical module entrypoint:

```bash
python3 -m agent_maintainer verify --profile fast
python3 -m agent_maintainer verify --profile precommit
```

If Codex reports a trusted Stop hook pass for the final repo state, do not start
another manual `precommit` run unless the repo changed after that pass or the
Codex hooks check verifier readiness before starting new work. If the same repo
state already has a verifier running, the hook reports a compact wait command.
If that same-state verifier has completed, the hook reuses the pass or failure
result. A changed working tree, index, profile, base, or compare state requires a
fresh verifier run.

failure needs reproduction. The verifier lock and same-state result cache reduce
exact duplicates, but the agent should still avoid unnecessary overlapping runs.

They prefer `.venv/bin/python` or `venv/bin/python` when present. Run `python3 -m agent_maintainer doctor` if hooks are configured but not behaving as expected.

## Audit Trail

Successful Codex hook passes are not guaranteed to appear in Codex session JSONL.
The hook scripts therefore append local audit records to:

```text
.verify-logs/hooks.jsonl
```

The audit records include the hook name, verifier profile, command, exit code,
status, timestamps, and duration. They intentionally do not include hook stdin,
prompt text, tool payloads, or verifier stdout/stderr.

`python3 -m agent_maintainer doctor` reports the latest audited hook status when
repo-local hooks are enabled.
<!-- docsync:object.end docs.codex_hooks.overview -->
