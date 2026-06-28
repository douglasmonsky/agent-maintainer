"""Install and inspect agent-client hook files."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agent_maintainer.hooks import merge, templates

CODEX_CLIENT = "codex"
CLAUDE_CODE_CLIENT = "claude-code"
ALL_CLIENTS = "all"
CLIENTS = (CODEX_CLIENT, CLAUDE_CODE_CLIENT)
REPO_SCOPE = "repo"
USER_SCOPE = "user"
SCOPES = (REPO_SCOPE, USER_SCOPE)


@dataclass(frozen=True)
class PlannedWrite:
    """One file write planned by hook installation."""

    path: Path
    content: str
    description: str
    merge_json: bool = False
    merge_codex: bool = False


@dataclass(frozen=True)
class InstallOptions:
    """Options controlling hook installation writes."""

    target: Path
    client: str
    scope: str = REPO_SCOPE
    force: bool = False
    yes: bool = False
    dry_run: bool = False


def selected_clients(client: str) -> tuple[str, ...]:
    """Return concrete clients selected by a CLI value."""

    return CLIENTS if client == ALL_CLIENTS else (client,)


def install_hooks(options: InstallOptions) -> int:
    """Install managed hook files for selected clients."""

    plans = tuple(
        plan
        for client in selected_clients(options.client)
        for plan in planned_writes(client, options)
    )
    if not plans:
        print("No hook files selected.")
        return 0
    print_plan(plans, options)
    if (
        options.scope == USER_SCOPE
        and not options.dry_run
        and not options.yes
        and not confirm_user_scope()
    ):
        print("Aborted without changing user-level hook configuration.")
        return 1
    for plan in plans:
        write_plan(plan, options)
    return 0


def planned_writes(client: str, options: InstallOptions) -> tuple[PlannedWrite, ...]:
    """Return planned writes for one hook client."""

    root = options.target.resolve()
    if client == CODEX_CLIENT:
        return codex_planned_writes(root, options.scope)
    if client == CLAUDE_CODE_CLIENT:
        return claude_planned_writes(root, options.scope)
    msg = f"Unsupported hook client: {client}"
    raise ValueError(msg)


def codex_planned_writes(root: Path, scope: str) -> tuple[PlannedWrite, ...]:
    """Return managed Codex writes."""

    config_path = (
        root / ".codex" / "config.toml"
        if scope == REPO_SCOPE
        else home() / ".codex" / "config.toml"
    )
    plans: tuple[PlannedWrite, ...] = (
        PlannedWrite(
            config_path,
            templates.codex_config_block(user_scope=scope == USER_SCOPE),
            "Codex hook config",
            merge_codex=True,
        ),
    )
    if scope == USER_SCOPE:
        return plans
    return (
        *plans,
        PlannedWrite(
            root / templates.CODEX_POST_HOOK,
            templates.codex_post_hook(),
            "Codex post-edit hook",
        ),
        PlannedWrite(
            root / templates.CODEX_STOP_HOOK,
            templates.codex_stop_hook(),
            "Codex stop hook",
        ),
        PlannedWrite(
            root / ".codex/hooks/hook_audit.py",
            templates.hook_audit_shim(),
            "Codex hook-audit compatibility shim",
        ),
    )


def claude_planned_writes(root: Path, scope: str) -> tuple[PlannedWrite, ...]:
    """Return managed Claude Code writes."""

    config_path = (
        root / ".claude" / "settings.json"
        if scope == REPO_SCOPE
        else home() / ".claude" / "settings.json"
    )
    plans: tuple[PlannedWrite, ...] = (
        PlannedWrite(
            config_path,
            templates.claude_settings(user_scope=scope == USER_SCOPE),
            "Claude Code hook settings",
            merge_json=True,
        ),
    )
    if scope == USER_SCOPE:
        return plans
    hook_root = root / ".claude/hooks"
    return (
        *plans,
        PlannedWrite(
            hook_root / "post_tool_use.py",
            templates.claude_post_hook(),
            "Claude Code post-edit hook",
        ),
        PlannedWrite(
            hook_root / "stop.py",
            templates.claude_stop_hook(),
            "Claude Code stop hook",
        ),
        PlannedWrite(
            hook_root / "subagent_stop.py",
            templates.claude_subagent_stop_hook(),
            "Claude Code subagent stop hook",
        ),
    )


def write_plan(plan: PlannedWrite, options: InstallOptions) -> None:
    """Write one planned hook file."""

    content = rendered_content(plan)
    if plan.path.exists() and plan.path.read_text(encoding="utf-8") == content:
        print(f"unchanged {plan.path}")
        return
    if options.dry_run:
        print(f"would write {plan.path}")
        return
    if plan.path.exists() and not options.force:
        backup_path = backup_existing(plan.path)
        print(f"backed up {plan.path} -> {backup_path}")
    plan.path.parent.mkdir(parents=True, exist_ok=True)
    plan.path.write_text(content, encoding="utf-8")
    print(f"wrote {plan.path}")


def rendered_content(plan: PlannedWrite) -> str:
    """Return merged content for one write plan."""

    if plan.merge_json and plan.path.exists():
        return merge.merge_claude_settings(plan.path, plan.content)
    if plan.merge_codex and plan.path.exists():
        return merge.merge_codex_config(
            plan.path.read_text(encoding="utf-8"),
            plan.content,
        )
    if plan.merge_codex:
        return merge.merge_codex_config("", plan.content)
    return plan.content


def backup_existing(path: Path) -> Path:
    """Create a timestamped backup next to an existing file."""

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = path.with_name(f"{path.name}.agent-maintainer-backup-{timestamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def print_plan(plans: tuple[PlannedWrite, ...], options: InstallOptions) -> None:
    """Print concise install plan."""

    print(f"Installing Agent Maintainer hooks: client={options.client} scope={options.scope}")
    for plan in plans:
        action = "merge" if plan.merge_json or plan.merge_codex else "write"
        print(f"  {action}: {plan.path} ({plan.description})")


def confirm_user_scope() -> bool:
    """Ask before mutating user-level agent client configuration."""

    answer = input("This will modify files under your home directory. Continue? [y/N] ")
    return answer.strip().casefold() in {"y", "yes"}


def status_hooks(target: Path, client: str, scope: str = REPO_SCOPE) -> int:
    """Print compact install status for selected clients."""

    root = target.resolve()
    for selected in selected_clients(client):
        config_path = config_file(selected, root, scope)
        scripts = hook_script_paths(selected, root, scope)
        config_status = "present" if config_path.exists() else "missing"
        scripts_status = "present" if all(path.exists() for path in scripts) else "missing"
        print(f"{selected}: config={config_status} scripts={scripts_status}")
    return 0


def config_file(client: str, root: Path, scope: str) -> Path:
    """Return config file path for one client."""

    if client == CODEX_CLIENT:
        return root / ".codex/config.toml" if scope == REPO_SCOPE else home() / ".codex/config.toml"
    if client == CLAUDE_CODE_CLIENT:
        return (
            root / ".claude/settings.json"
            if scope == REPO_SCOPE
            else home() / ".claude/settings.json"
        )
    msg = f"Unsupported hook client: {client}"
    raise ValueError(msg)


def hook_script_paths(client: str, root: Path, scope: str) -> tuple[Path, ...]:
    """Return expected hook script paths for one client."""

    if client == CODEX_CLIENT:
        base = root / ".codex/hooks" if scope == REPO_SCOPE else home() / ".codex/hooks"
        return (base / "post_edit_fast_gate.py", base / "stop_full_verify.py")
    if client == CLAUDE_CODE_CLIENT:
        base = root / ".claude/hooks" if scope == REPO_SCOPE else home() / ".claude/hooks"
        return (base / "post_tool_use.py", base / "stop.py", base / "subagent_stop.py")
    msg = f"Unsupported hook client: {client}"
    raise ValueError(msg)


def home() -> Path:
    """Return the current user's home directory."""

    return Path.home()
