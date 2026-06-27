"""Generated hook templates for supported agent clients."""

from __future__ import annotations

import json
import textwrap

from agent_maintainer.hooks.runtime import (
    CLAUDE_CODE_PLATFORM,
    CODEX_PLATFORM,
    POST_TOOL_USE_EVENT,
    STOP_EVENT,
    SUBAGENT_STOP_EVENT,
)

MANAGED_PREFIX = "agent-maintainer"
CODEX_MARKER = f"{MANAGED_PREFIX}:codex-hooks"
CODEX_POST_HOOK = ".codex/hooks/post_edit_fast_gate.py"
CODEX_STOP_HOOK = ".codex/hooks/stop_full_verify.py"
CLAUDE_POST_HOOK = ".claude/hooks/post_tool_use.py"
CLAUDE_STOP_HOOK = ".claude/hooks/stop.py"
CLAUDE_SUBAGENT_STOP_HOOK = ".claude/hooks/subagent_stop.py"


def codex_config_block(*, user_scope: bool = False) -> str:
    """Return the managed Codex hook configuration block."""

    post_command = hook_command(
        platform=CODEX_PLATFORM,
        event=POST_TOOL_USE_EVENT,
        profile="fast",
        wrapper_path=CODEX_POST_HOOK,
        user_scope=user_scope,
    )
    stop_command = hook_command(
        platform=CODEX_PLATFORM,
        event=STOP_EVENT,
        profile="precommit",
        wrapper_path=CODEX_STOP_HOOK,
        user_scope=user_scope,
    )
    body = textwrap.dedent(
        f"""\
        [[hooks.PostToolUse]]
        matcher = "apply_patch|Edit|Write|MultiEdit"

        [[hooks.PostToolUse.hooks]]
        type = "command"
        command = {json.dumps(post_command)}
        timeout = 60
        statusMessage = "Running fast Agent Maintainer checks"

        [[hooks.Stop]]

        [[hooks.Stop.hooks]]
        type = "command"
        command = {json.dumps(stop_command)}
        timeout = 600
        statusMessage = "Running final Agent Maintainer verification"
        """
    ).strip()
    return managed_toml_block(CODEX_MARKER, body)


def codex_config_file(*, user_scope: bool = False) -> str:
    """Return complete Codex hook config for new installations."""

    return f"[features]\nhooks = true\n\n{codex_config_block(user_scope=user_scope)}"


def claude_settings(*, user_scope: bool = False) -> str:
    """Return project-local Claude Code hook settings JSON."""

    post_command = hook_command(
        platform=CLAUDE_CODE_PLATFORM,
        event=POST_TOOL_USE_EVENT,
        profile="fast",
        wrapper_path=CLAUDE_POST_HOOK,
        user_scope=user_scope,
    )
    stop_command = hook_command(
        platform=CLAUDE_CODE_PLATFORM,
        event=STOP_EVENT,
        profile="precommit",
        wrapper_path=CLAUDE_STOP_HOOK,
        user_scope=user_scope,
    )
    subagent_stop_command = hook_command(
        platform=CLAUDE_CODE_PLATFORM,
        event=SUBAGENT_STOP_EVENT,
        profile="precommit",
        wrapper_path=CLAUDE_SUBAGENT_STOP_HOOK,
        user_scope=user_scope,
    )
    data = {
        "hooks": {
            POST_TOOL_USE_EVENT: [
                {
                    "matcher": "Write|Edit|MultiEdit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": post_command,
                            "timeout": 60,
                        }
                    ],
                }
            ],
            STOP_EVENT: [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": stop_command,
                            "timeout": 600,
                        }
                    ]
                }
            ],
            SUBAGENT_STOP_EVENT: [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": subagent_stop_command,
                            "timeout": 600,
                        }
                    ]
                }
            ],
        }
    }
    return f"{json.dumps(data, indent=2, sort_keys=True)}\n"


def hook_command(
    *,
    platform: str,
    event: str,
    profile: str,
    wrapper_path: str,
    user_scope: bool,
) -> str:
    """Return hook command for repo-local or user-level installation."""

    if user_scope:
        return (
            f"agent-maintainer hooks run --platform {platform} --event {event} --profile {profile}"
        )
    return f'python3 "$(git rev-parse --show-toplevel)/{wrapper_path}"'


def hook_wrapper(*, platform: str, event: str, profile: str) -> str:
    """Return repo-local Python hook wrapper."""

    return textwrap.dedent(
        f"""
        \"\"\"Agent Maintainer {platform} {event} hook wrapper.\"\"\"

        from __future__ import annotations

        import importlib
        import sys
        from pathlib import Path

        REPO_ROOT = Path(__file__).resolve().parents[2]
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(REPO_ROOT / "src"))

        run_hook = importlib.import_module("agent_maintainer.hooks.runtime").run_hook


        def main() -> int:
            \"\"\"Run shared Agent Maintainer hook runtime.\"\"\"

            return run_hook(
                platform="{platform}",
                event="{event}",
                profile="{profile}",
                repo_root=REPO_ROOT,
            )


        if __name__ == "__main__":
            sys.exit(main())
        """
    ).lstrip()


def codex_post_hook() -> str:
    """Return Codex PostToolUse wrapper source."""

    return hook_wrapper(platform=CODEX_PLATFORM, event=POST_TOOL_USE_EVENT, profile="fast")


def codex_stop_hook() -> str:
    """Return Codex Stop wrapper source."""

    return hook_wrapper(platform=CODEX_PLATFORM, event=STOP_EVENT, profile="precommit")


def claude_post_hook() -> str:
    """Return Claude Code PostToolUse wrapper source."""

    return hook_wrapper(platform=CLAUDE_CODE_PLATFORM, event=POST_TOOL_USE_EVENT, profile="fast")


def claude_stop_hook() -> str:
    """Return Claude Code Stop wrapper source."""

    return hook_wrapper(platform=CLAUDE_CODE_PLATFORM, event=STOP_EVENT, profile="precommit")


def claude_subagent_stop_hook() -> str:
    """Return Claude Code SubagentStop wrapper source."""

    return hook_wrapper(
        platform=CLAUDE_CODE_PLATFORM,
        event=SUBAGENT_STOP_EVENT,
        profile="precommit",
    )


def hook_audit_shim() -> str:
    """Return compatibility shim for older repo-local hook tests/imports."""

    return textwrap.dedent(
        """
        \"\"\"Compatibility imports repo-local Agent Maintainer hook audit.\"\"\"

        from __future__ import annotations

        import importlib
        import sys
        from pathlib import Path

        REPO_ROOT = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(REPO_ROOT / "src"))

        _AUDIT = importlib.import_module("agent_maintainer.hooks.audit")
        __all__ = tuple(name for name in dir(_AUDIT) if not name.startswith("_"))
        globals().update({name: getattr(_AUDIT, name) for name in __all__})
        """
    ).lstrip()


def managed_toml_block(marker: str, body: str) -> str:
    """Return a fenced managed TOML block."""

    return f"# >>> {marker} >>>\n{body.rstrip()}\n# <<< {marker} <<<\n"
