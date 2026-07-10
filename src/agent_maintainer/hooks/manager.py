"""Install and inspect agent-client hook files."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from agent_client_hooks import adapters as hook_adapters
from agent_client_hooks import merge

ALL_CLIENTS = hook_adapters.ALL_CLIENTS
CLIENTS = hook_adapters.CLIENTS
CLAUDE_CODE_CLIENT = hook_adapters.CLAUDE_CODE_CLIENT
CODEX_CLIENT = hook_adapters.CODEX_CLIENT
InstallOptions = hook_adapters.InstallOptions
PlannedWrite = hook_adapters.PlannedWrite
REPO_SCOPE = hook_adapters.REPO_SCOPE
SCOPES = hook_adapters.SCOPES
USER_SCOPE = hook_adapters.USER_SCOPE


def selected_clients(client: str) -> tuple[str, ...]:
    """Return concrete clients selected by CLI value."""
    return hook_adapters.selected_clients(client)


def install_hooks(options: InstallOptions) -> int:
    """Install managed hook clients."""
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
        print("Aborted without user-level configuration.")
        return 1
    for plan in plans:
        write_plan(plan, options)
    return 0


def planned_writes(client: str, options: InstallOptions) -> tuple[PlannedWrite, ...]:
    """Return planned writes for one hook client."""
    adapter = hook_adapters.adapter_for_client(client)
    if isinstance(adapter, hook_adapters.ClaudeCodeAdapter):
        return adapter.install(
            options.target,
            options.scope,
            async_rewake_stop=options.async_rewake_stop,
        )
    return adapter.install(options.target, options.scope)


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
    """Back up existing file and return backup path."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    backup_path = path.with_name(f"{path.name}.agent-maintainer-backup-{timestamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def print_plan(plans: tuple[PlannedWrite, ...], options: InstallOptions) -> None:
    """Print planned writes before installation."""
    scope_label = "user" if options.scope == USER_SCOPE else "repo"
    print(f"Agent Maintainer hook install ({scope_label} scope):")
    for plan in plans:
        print(f"- {plan.description}: {plan.path}")
    if options.dry_run:
        print("dry-run: no files written")


def confirm_user_scope() -> bool:
    """Return whether user confirmed global user-scope hook writes."""
    response = input("Write Agent Maintainer hooks to user-level agent config? [y/N] ")
    return response.strip().lower() in {"y", "yes"}


def status_hooks(target: Path, client: str, scope: str = REPO_SCOPE) -> int:
    """Print compact install status for selected clients."""
    root = target.resolve()
    for selected in selected_clients(client):
        status = hook_adapters.adapter_for_client(selected).status(root, scope)
        config_status = status_label(status.config_present, status.config_current)
        scripts_status = (
            status_label(status.scripts_present, status.scripts_current)
            if status.scripts_expected
            else "not-managed"
        )
        print(f"{selected}: config={config_status} scripts={scripts_status}")
    return 0


def status_label(present: bool, current: bool) -> str:
    """Return a compact managed-file status label."""

    if not present:
        return "missing"
    return "current" if current else "stale"


def config_file(client: str, root: Path, scope: str) -> Path:
    """Return config file path for one client."""
    return hook_adapters.config_file(client, root, scope)


def hook_script_paths(client: str, root: Path, scope: str) -> tuple[Path, ...]:
    """Return expected hook script paths for one client."""
    return hook_adapters.hook_script_paths(client, root, scope)


def home() -> Path:
    """Return user's home directory."""
    return hook_adapters.home()
