# Codex Hooks

The kit includes repo-local Codex hooks under `.codex/`:

| Hook | Purpose |
|---|---|
| `PostToolUse` | Runs the fast profile after file edits and feeds failures back into the turn. |
| `Stop` | Runs the precommit profile before the agent finishes. |

Install local hooks with:

```bash
python3 -m scripts.guardrail install
```

This installs the pre-commit hook when available and reports whether `.codex/config.toml` exists. It does not approve Codex hooks for you.

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
python3 -m scripts.guardrail verify --profile fast
python3 -m scripts.guardrail verify --profile precommit
```

They prefer `.venv/bin/python` or `venv/bin/python` when present. Run `python3 -m scripts.guardrail doctor` if hooks are configured but not behaving as expected.
