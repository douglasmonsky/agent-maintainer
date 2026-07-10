"""Install and inspect agent-client hook files."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from agent_client_hooks import adapters as hook_adapters
from agent_client_hooks import merge
from agent_maintainer.hooks import mutations

ALL_CLIENTS = hook_adapters.ALL_CLIENTS
CLIENTS = hook_adapters.CLIENTS
CLAUDE_CODE_CLIENT = hook_adapters.CLAUDE_CODE_CLIENT
CODEX_CLIENT = hook_adapters.CODEX_CLIENT
InstallOptions = hook_adapters.InstallOptions
PlannedWrite = hook_adapters.PlannedWrite
REPO_SCOPE = hook_adapters.REPO_SCOPE
SCOPES = hook_adapters.SCOPES
USER_SCOPE = hook_adapters.USER_SCOPE


class MutationOptions(Protocol):
    """Common options required by the transactional mutation boundary."""

    @property
    def target(self) -> Path:
        """Return the repository target."""
        raise NotImplementedError

    @property
    def scope(self) -> str:
        """Return repository or user mutation scope."""
        raise NotImplementedError

    @property
    def dry_run(self) -> bool:
        """Return whether the operation is preview-only."""
        raise NotImplementedError


def selected_clients(client: str) -> tuple[str, ...]:
    """Return concrete clients selected by CLI value."""
    return hook_adapters.selected_clients(client)


def install_hooks(options: InstallOptions, *, operation: str = "install") -> int:
    """Install or update managed hook clients through one mutation contract."""

    return _install_or_update(options, operation=operation)


def _install_or_update(options: InstallOptions, *, operation: str) -> int:
    """Prepare and apply one install-like hook lifecycle operation."""

    plans = tuple(
        plan
        for client in selected_clients(options.client)
        for plan in planned_writes(client, options)
    )
    if not plans:
        print("No hook files selected.")
        return 0
    try:
        prepared = prepare_writes(plans, force=options.force)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"FAIL hook {operation}: cannot prepare writes: {exc}")
        return 1
    print_plan(plans, options, operation=operation)
    if (
        options.scope == USER_SCOPE
        and not options.dry_run
        and not options.yes
        and not confirm_user_scope()
    ):
        print("Aborted without user-level configuration.")
        return 1
    return apply_prepared_writes(prepared, options, operation=operation)


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
    prepared = mutations.prepare_write(
        plan,
        rendered_content(plan, force=options.force),
    )
    if not prepared.changed:
        print(f"unchanged {plan.path}")
        return
    if options.dry_run:
        print(f"would write {plan.path}")
        return
    apply_prepared_writes((prepared,), options)


def rendered_content(plan: PlannedWrite, *, force: bool = False) -> str:
    """Return merged content for one write plan."""
    try:
        return _merged_or_direct_content(plan)
    except (OSError, UnicodeError, ValueError):
        if force:
            return plan.content
        raise


def _merged_or_direct_content(plan: PlannedWrite) -> str:
    """Return merged content without conflict recovery."""

    if plan.merge_json and plan.path.exists():
        return merge.merge_claude_settings(plan.path, plan.content)
    if plan.merge_codex and plan.path.exists():
        existing = plan.path.read_text(encoding="utf-8")
        return merge.merge_codex_config(existing, plan.content)
    if plan.merge_codex:
        return merge.merge_codex_config("", plan.content)
    return plan.content


def prepare_writes(
    plans: tuple[PlannedWrite, ...],
    *,
    force: bool,
) -> tuple[mutations.PreparedHookWrite, ...]:
    """Render and inspect every plan before the first mutation."""

    return tuple(
        mutations.prepare_write(plan, rendered_content(plan, force=force)) for plan in plans
    )


def apply_prepared_writes(
    prepared: tuple[mutations.PreparedHookWrite, ...],
    options: MutationOptions,
    *,
    operation: str = "install",
) -> int:
    """Preview or transactionally apply prepared hook writes."""

    if options.dry_run:
        _print_prepared(prepared, dry_run=True)
        return 0
    try:
        result = mutations.apply_transaction(
            prepared,
            ownership_root=_ownership_root(options),
            git_private=options.scope == REPO_SCOPE,
        )
    except mutations.HookMutationError as exc:
        print(f"FAIL hook {operation}: {exc}")
        return 1
    for backup in result.backups:
        print(f"backed up {backup.original} -> {backup.backup}")
    _print_prepared(prepared, dry_run=False)
    if result.rollback_manifest is not None:
        print(f"rollback manifest: {result.rollback_manifest}")
    return 0


def _print_prepared(
    prepared: tuple[mutations.PreparedHookWrite, ...],
    *,
    dry_run: bool,
) -> None:
    """Print one action line for each prepared destination."""

    for item in prepared:
        path = item.plan.path
        action = _prepared_action(item, dry_run=dry_run)
        print(action, path)


def _prepared_action(item: mutations.PreparedHookWrite, *, dry_run: bool) -> str:
    """Return the visible action for one prepared destination."""

    if item.changed and item.content is None:
        return "would remove" if dry_run else "removed"
    if item.changed:
        return "would write" if dry_run else "wrote"
    return "unchanged"


def _ownership_root(options: MutationOptions) -> Path:
    """Return the root that owns destinations and rollback data."""

    if options.scope == USER_SCOPE:
        return hook_adapters.home()
    return options.target.resolve()


def print_plan(
    plans: tuple[PlannedWrite, ...],
    options: InstallOptions,
    *,
    operation: str = "install",
) -> None:
    """Print planned writes before installation."""
    scope_label = "user" if options.scope == USER_SCOPE else "repo"
    print(f"Agent Maintainer hook {operation} ({scope_label} scope):")
    for plan in plans:
        print(f"- {plan.description}: {plan.path}")
    if options.dry_run:
        print("dry-run: no files written")


def confirm_user_scope(operation: str = "write") -> bool:
    """Return whether user confirmed global user-scope hook writes."""
    response = input(
        f"{operation.capitalize()} Agent Maintainer hooks in user-level agent config? [y/N] "
    )
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
