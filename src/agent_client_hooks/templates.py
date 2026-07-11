"""Generated hook templates for supported agent clients."""

from __future__ import annotations

import json
import textwrap

from agent_client_hooks.constants import (
    CLAUDE_CODE_PLATFORM,
    CODEX_PLATFORM,
    POST_TOOL_USE_EVENT,
    STOP_EVENT,
    SUBAGENT_STOP_EVENT,
)

MANAGED_PREFIX = "agent-maintainer"
CODEX_MARKER = f"{MANAGED_PREFIX}:codex-hooks"
CODEX_POST_HOOK = ".codex/hooks/post_edit_fast_gate.py"
CODEX_PR_WAIT_HOOK = ".codex/hooks/post_pr_wait.py"
CODEX_STOP_HOOK = ".codex/hooks/stop_full_verify.py"
CLAUDE_POST_HOOK = ".claude/hooks/post_tool_use.py"
CLAUDE_PR_WAIT_HOOK = ".claude/hooks/post_pr_wait.py"
CLAUDE_STOP_HOOK = ".claude/hooks/stop.py"
CLAUDE_SUBAGENT_STOP_HOOK = ".claude/hooks/subagent_stop.py"


# docsync:evidence.start evidence.agent_hooks.generated_templates
def codex_config_block(*, user_scope: bool = False) -> str:
    """Return the managed Codex hook configuration block."""

    post_command = hook_command(
        platform=CODEX_PLATFORM,
        event=POST_TOOL_USE_EVENT,
        profile="fast",
        wrapper_path=CODEX_POST_HOOK,
        user_scope=user_scope,
    )
    pr_wait_command = pr_wait_command_for(
        platform=CODEX_PLATFORM,
        wrapper_path=CODEX_PR_WAIT_HOOK,
        user_scope=user_scope,
        async_rewake=False,
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

        [[hooks.PostToolUse]]
        matcher = "Bash"

        [[hooks.PostToolUse.hooks]]
        type = "command"
        command = {json.dumps(pr_wait_command)}
        timeout = 30
        statusMessage = "Checking PR wait handoff"

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


def claude_settings(
    *,
    user_scope: bool = False,
    async_rewake_stop: bool = False,
) -> str:
    """Return project-local Claude Code hook settings JSON."""

    post_command = hook_command(
        platform=CLAUDE_CODE_PLATFORM,
        event=POST_TOOL_USE_EVENT,
        profile="fast",
        wrapper_path=CLAUDE_POST_HOOK,
        user_scope=user_scope,
    )
    pr_wait_command = pr_wait_command_for(
        platform=CLAUDE_CODE_PLATFORM,
        wrapper_path=CLAUDE_PR_WAIT_HOOK,
        user_scope=user_scope,
        async_rewake=True,
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
    if async_rewake_stop and user_scope:
        stop_command = f"{stop_command} --async-rewake"
        subagent_stop_command = f"{subagent_stop_command} --async-rewake"
    stop_hook = {
        "type": "command",
        "command": stop_command,
        "timeout": 600,
    }
    subagent_stop_hook = {
        "type": "command",
        "command": subagent_stop_command,
        "timeout": 600,
    }
    pr_wait_hook = {
        "type": "command",
        "command": pr_wait_command,
        "timeout": 1800,
        "async": True,
        "asyncRewake": True,
    }
    if async_rewake_stop:
        stop_hook.update({"async": True, "asyncRewake": True})
        subagent_stop_hook.update({"async": True, "asyncRewake": True})
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
                },
                {
                    "matcher": "Bash",
                    "hooks": [pr_wait_hook],
                },
            ],
            STOP_EVENT: [{"hooks": [stop_hook]}],
            SUBAGENT_STOP_EVENT: [{"hooks": [subagent_stop_hook]}],
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


def pr_wait_command_for(
    *,
    platform: str,
    wrapper_path: str,
    user_scope: bool,
    async_rewake: bool,
) -> str:
    """Return PR wait hook command for repo-local or user-level installation."""
    if user_scope:
        command = f"agent-maintainer hooks pr-wait --platform {platform}"
        if async_rewake:
            return f"{command} --async-rewake"
        return command
    return f'python3 "$(git rev-parse --show-toplevel)/{wrapper_path}"'


def hook_wrapper(
    *,
    platform: str,
    event: str,
    profile: str,
    async_rewake: bool = False,
) -> str:
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
                async_rewake={async_rewake!r},
            )


        if __name__ == "__main__":
            sys.exit(main())
        """
    ).lstrip()


def pr_wait_hook_wrapper(*, platform: str, async_rewake: bool) -> str:
    """Return repo-local PR wait hook wrapper."""
    return textwrap.dedent(
        f"""
            \"\"\"Agent Maintainer {platform} PR wait hook wrapper.\"\"\"

            from __future__ import annotations

            import importlib
            import sys
            from pathlib import Path

            REPO_ROOT = Path(__file__).resolve().parents[2]
            sys.dont_write_bytecode = True
            sys.path.insert(0, str(REPO_ROOT / "src"))

            run_hook = importlib.import_module("agent_maintainer.hooks.pr_wait").run_hook


            def main() -> int:
                \"\"\"Run Agent Maintainer PR wait hook.\"\"\"

                return run_hook(
                    platform="{platform}",
                    repo_root=REPO_ROOT,
                    async_rewake={async_rewake!r},
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


def codex_pr_wait_hook() -> str:
    """Return Codex PR wait hook wrapper source."""
    return pr_wait_hook_wrapper(platform=CODEX_PLATFORM, async_rewake=False)


def claude_post_hook() -> str:
    """Return Claude Code PostToolUse wrapper source."""

    return hook_wrapper(platform=CLAUDE_CODE_PLATFORM, event=POST_TOOL_USE_EVENT, profile="fast")


def claude_pr_wait_hook() -> str:
    """Return Claude Code PR wait hook wrapper source."""
    return pr_wait_hook_wrapper(platform=CLAUDE_CODE_PLATFORM, async_rewake=True)


def claude_stop_hook(*, async_rewake: bool = False) -> str:
    """Return Claude Code Stop wrapper source."""

    return hook_wrapper(
        platform=CLAUDE_CODE_PLATFORM,
        event=STOP_EVENT,
        profile="precommit",
        async_rewake=async_rewake,
    )


def claude_subagent_stop_hook(*, async_rewake: bool = False) -> str:
    """Return Claude Code SubagentStop wrapper source."""

    return hook_wrapper(
        platform=CLAUDE_CODE_PLATFORM,
        event=SUBAGENT_STOP_EVENT,
        profile="precommit",
        async_rewake=async_rewake,
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
        HookAuditRecord = _AUDIT.HookAuditRecord
        record_hook_result = _AUDIT.record_hook_result
        status_for_exit = _AUDIT.status_for_exit
        """
    ).lstrip()


# docsync:evidence.end evidence.agent_hooks.generated_templates
def managed_toml_block(marker: str, body: str) -> str:
    """Return a fenced managed TOML block."""

    return f"# >>> {marker} >>>\n{body.rstrip()}\n# <<< {marker} <<<\n"
