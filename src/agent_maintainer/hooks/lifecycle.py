"""Update and safely remove manifest-owned agent-client hooks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_client_hooks import adapters as hook_adapters
from agent_client_hooks import manifest, removal
from agent_maintainer.hooks import manager, mutations


@dataclass(frozen=True)
class UninstallOptions:
    """Options controlling managed-hook removal."""

    target: Path
    client: str
    scope: str = manager.REPO_SCOPE
    force: bool = False
    yes: bool = False
    dry_run: bool = False


def update_hooks(options: manager.InstallOptions) -> int:
    """Update managed hooks through the lossless install mutation contract."""

    return manager.install_hooks(options, operation="update")


def uninstall_hooks(options: UninstallOptions) -> int:
    """Remove only configuration entries and files owned by the manifest."""

    try:
        prepared = prepare_uninstall(options)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"FAIL hook uninstall: cannot prepare removals: {exc}")
        return 1
    print_uninstall_plan(prepared, options)
    if _user_scope_refused(options):
        print("Aborted without changing user-level configuration.")
        return 1
    return manager.apply_prepared_writes(prepared, options, operation="uninstall")


def prepare_uninstall(options: UninstallOptions) -> tuple[mutations.PreparedHookWrite, ...]:
    """Preflight every manifest-owned removal before any mutation."""

    root = options.target.resolve()
    return tuple(
        _prepare_uninstall_item(
            item,
            hook_adapters.scoped_path(root, options.scope, item.relative_path),
            force=options.force,
        )
        for client in manager.selected_clients(options.client)
        for item in manifest.managed_files(client, scope=options.scope)
        if item.uninstall
    )


def _user_scope_refused(options: UninstallOptions) -> bool:
    """Return whether an interactive user-scope removal was declined."""

    return (
        options.scope == manager.USER_SCOPE
        and not options.dry_run
        and not options.yes
        and not manager.confirm_user_scope("remove")
    )


def _prepare_uninstall_item(
    item: manifest.ManagedHookFile,
    path: Path,
    *,
    force: bool,
) -> mutations.PreparedHookWrite:
    """Return a safe write or delete for one manifest record."""

    plan = manager.PlannedWrite(path, "", item.description)
    if path.is_symlink():
        raise ValueError(f"refusing symlinked managed path: {path}")
    if not path.exists():
        return mutations.prepare_delete(plan)
    if not path.is_file():
        raise ValueError(f"refusing non-file managed path: {path}")
    existing = path.read_text(encoding="utf-8")
    if item.kind == manifest.CONFIG_KIND:
        return _prepare_config_uninstall(plan, item, existing)
    return _prepare_script_uninstall(plan, item, existing, force=force)


def _prepare_config_uninstall(
    plan: manager.PlannedWrite,
    item: manifest.ManagedHookFile,
    existing: str,
) -> mutations.PreparedHookWrite:
    """Remove only stable managed identities from one client config."""

    remaining = _remaining_config(item, existing, path=plan.path)
    if not remaining:
        return mutations.prepare_delete(plan)
    return mutations.prepare_write(plan, remaining)


def _remaining_config(
    item: manifest.ManagedHookFile,
    existing: str,
    *,
    path: Path,
) -> str:
    """Return client config after managed identities are removed."""

    if item.merge_strategy == "codex-toml":
        return removal.remove_codex_config(existing)
    if item.merge_strategy == "claude-json":
        return removal.remove_claude_settings(existing)
    raise ValueError(f"unsupported managed config removal: {path}")


def _prepare_script_uninstall(
    plan: manager.PlannedWrite,
    item: manifest.ManagedHookFile,
    existing: str,
    *,
    force: bool,
) -> mutations.PreparedHookWrite:
    """Remove current scripts, or explicitly forced stale owned scripts."""

    expected = {
        manifest.render(item, options=manifest.RenderOptions(async_rewake_stop=async_rewake))
        for async_rewake in (False, True)
    }
    if existing in expected:
        return mutations.prepare_delete(plan)
    path = plan.path
    if item.ownership_marker not in existing:
        raise ValueError(f"refusing to remove unowned file: {path}")
    if not force:
        raise ValueError(f"stale managed file requires --force: {path}")
    return mutations.prepare_delete(plan)


def print_uninstall_plan(
    prepared: tuple[mutations.PreparedHookWrite, ...],
    options: UninstallOptions,
) -> None:
    """Print preflighted managed removals."""

    scope_label = "user" if options.scope == manager.USER_SCOPE else "repo"
    print(f"Agent Maintainer hook uninstall ({scope_label} scope):")
    for item in prepared:
        plan = item.plan
        print(f"- {plan.description}: {plan.path}")
    if options.dry_run:
        print("dry-run: no files written")
