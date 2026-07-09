<!-- docsync:object docs.codex_hooks.overview -->
# Codex Hooks

For the full managed hook installer covering Codex and Claude Code, see
[Agent client hooks](agent-client-hooks.md).

Claude Code installations can opt into asynchronous rewake for slow
`Stop`/`SubagentStop` validation through the shared installer:
`python3 -m agent_maintainer hooks install claude-code --async-rewake-stop`.
In that mode, generated Claude stop hooks pass runtime async-rewake mode and
return exit `2` with compact wait/repair context when verification is pending or
failed, so Claude Code wakes back into the turn.

The kit includes repo-local Codex hooks under `.codex/`:

| Hook | Purpose |
|---|---|
| `PostToolUse` | Runs fast profile after file edits and feeds failures back into the turn. |
| `Stop` | Runs precommit profile before the agent finishes. |

Install Codex hooks with:

```bash
python3 -m agent_maintainer hooks install codex
```

`python3 -m agent_maintainer install` also installs managed agent-client hooks
and local pre-commit setup. It does not approve Codex hooks for you.

## Trust Review

Codex hook trust is source-hash specific. Treat trust as tied to the exact hook
configuration and hook script contents, not permanent approval for every future
edit.

Re-review hooks after any change to:

- `.codex/config.toml`
- `.codex/hooks/post_edit_fast_gate.py`
- `.codex/hooks/stop_full_verify.py`
- the command each hook runs
- repo path copied into hook source

Hook commands should remain repo-local and should not transmit private,
student, financial, credential-bearing, or production data. This kit's hooks run
local verification only.

## Expected Commands

Hook scripts invoke the canonical module entrypoint:

```bash
python3 -m agent_maintainer verify --profile fast
python3 -m agent_maintainer verify --profile precommit
```

When Codex reports a trusted Stop hook pass for the final repo state, do not
start another manual `precommit` run unless the repo changed after that pass.
Codex hooks check verifier readiness before starting new work. If the same repo
state already has a verifier running, the hook reports a compact background wait
handoff. If same-state verifier completed, the hook reuses the pass or failure
result. A changed working tree, index, profile, base, or compare state requires a
fresh verifier run.

If failure needs reproduction, verifier lock and same-state result cache reduce
exact duplicates, but the agent should still avoid unnecessary overlapping runs.

Prefer `.venv/bin/python` or `venv/bin/python` when present. Run
`python3 -m agent_maintainer doctor` when hooks are configured but not behaving
as expected.

A Bash `gh pr create` `PostToolUse` hook detects created PR URLs, registers a
durable wait record under `.verify-logs/waits/`, and starts a detached local
watcher. Codex gets one compact message with a manual `wait resume <id>`
command and a structured heartbeat request for thread automation. Pending
checks must not produce repeated chat updates.

Codex PR, GitHub run, and verifier waits use background ownership by default.
On macOS Codex, registration first ensures a repo-scoped user LaunchAgent with
label `com.agent-maintainer.wait.<stable-root-hash>`. The plist excludes thread
ids, prompts, API keys, hook stdin, and private payloads. Codex waits do not
silently fall back to a detached `popen` watcher when launchd cannot start;
registration reports the launchd failure and leaves the wait recoverable by
`wait sweep` / `wait resume`. Manage the
daemon with `python -m agent_maintainer wait daemon install|status|uninstall
--root <repo>`.
Set `AGENT_MAINTAINER_BACKGROUND_PR_WAIT=0` only when debugging the old PR
foreground handoff path, or `AGENT_MAINTAINER_BACKGROUND_WAIT=0` to debug all
known wait foreground paths. Direct foreground `wait github-pr`,
`wait github-run`, and `wait verifier` commands also convert to background
registration inside Codex unless `AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1` is
set. Direct Codex verifier commands such as `python -m agent_maintainer verify --profile ci`
and repo `just v` / `just vc` wrappers start an async verifier and emit the
same background wait heartbeat handoff by default.

Codex heartbeat requests are wait-scoped. When the Codex app
`automation_update` tool is available, create one current-thread heartbeat
that runs `python -m agent_maintainer wait sweep --one <wait-id> --root
<repo>`. The heartbeat request includes `on_pending: silent`, `on_terminal:
resume_and_review`, and `merge_policy: merge_only_if_satisfactory`. The
targeted sweep command polls only that wait once, prints nothing while the
wait is pending, and prints its terminal resume capsule once. Use `python -m
agent_maintainer wait cleanup --root <repo>` to expire stale ready records
after a terminal wait is no longer useful.

Set `AGENT_MAINTAINER_CODEX_REWAKE=1` to let terminal background watchers try
automatic Codex continuation. The preferred backend is the local Codex CLI app-server
`codex app-server --listen stdio://` with Codex thread metadata from
`CODEX_THREAD_ID` or `AGENT_MAINTAINER_CODEX_THREAD_ID`; optional
`openai-codex` SDK remains fallback backend. If app-server, SDK, auth, or
thread metadata is unavailable, the wait stays ready for the manual
`wait resume <id>` command. No thread id or prompt is stored in the wait record.

Terminal-only local polling is the preferred path; automatic visible Codex
thread rewake is not treated as proven today.
`AGENT_MAINTAINER_CODEX_REWAKE=1` may attempt app-server handoff, but app-server
turn acceptance does not mark a wait `resumed` because it has not proven visible
desktop wake. Terminal waits therefore remain ready for manual
`wait resume <id>` recovery until Codex exposes a supported visible-thread
resume surface. Heartbeat fallback still wakes a model each interval; use it
only when explicit manual monitoring is acceptable.

## Audit Trail

Successful Codex hook passes are not guaranteed to appear in Codex session JSONL.
Agent Maintainer writes its own local audit trail:

```text
.verify-logs/hooks.jsonl
```

Audit records include hook name, verifier profile, command, exit code, status,
timestamps, and duration. They intentionally do not include hook stdin, prompt
text, tool payloads, or verifier stdout/stderr.

`python3 -m agent_maintainer doctor` reports latest audited hook status and
repo-local hooks enabled.
<!-- docsync:object.end docs.codex_hooks.overview -->
