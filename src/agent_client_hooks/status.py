"""Currentness checks for managed agent-client files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_client_hooks import constants, manifest, merge


@dataclass(frozen=True)
class HookClientStatus:
    """Computed lifecycle status for one managed agent client."""

    name: str
    config_present: bool
    scripts_present: bool
    config_current: bool
    scripts_current: bool
    scripts_expected: bool


def client_status(
    client: str,
    target: Path,
    scope: str,
    *,
    user_root: Path,
) -> HookClientStatus:
    """Return manifest-derived install and currentness status."""

    root = target.resolve()
    scoped_files = manifest.managed_files(client, scope=scope)
    configs = tuple(item for item in scoped_files if item.kind == manifest.CONFIG_KIND)
    scripts = tuple(item for item in scoped_files if item.kind == manifest.SCRIPT_KIND)
    config_present = _all_present(root, user_root, scope, configs)
    scripts_present = _all_present(root, user_root, scope, scripts)
    return HookClientStatus(
        client,
        config_present,
        scripts_present,
        config_present and _all_current(root, user_root, scope, configs),
        scripts_present and _all_current(root, user_root, scope, scripts),
        bool(scripts),
    )


def _all_present(
    root: Path,
    user_root: Path,
    scope: str,
    records: tuple[manifest.ManagedHookFile, ...],
) -> bool:
    """Return whether every selected manifest path exists."""

    return all(
        _scoped_path(root, user_root, scope, item.relative_path).exists() for item in records
    )


def _all_current(
    root: Path,
    user_root: Path,
    scope: str,
    records: tuple[manifest.ManagedHookFile, ...],
) -> bool:
    """Return whether every selected manifest path matches a valid rendering."""

    return all(
        _managed_file_current(
            _scoped_path(root, user_root, scope, item.relative_path),
            item,
            scope=scope,
        )
        for item in records
    )


def _managed_file_current(
    path: Path,
    item: manifest.ManagedHookFile,
    *,
    scope: str,
) -> bool:
    """Return whether one existing file is current for a supported variant."""

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return any(
        _content_current(path, content, item, options=options)
        for options in _status_render_options(item, scope=scope)
    )


def _status_render_options(
    item: manifest.ManagedHookFile,
    *,
    scope: str,
) -> tuple[manifest.RenderOptions, ...]:
    """Return accepted status variants for one manifest file."""

    default = manifest.RenderOptions(user_scope=scope == constants.USER_SCOPE)
    if item.client != constants.CLAUDE_CODE_CLIENT:
        return (default,)
    return (
        default,
        manifest.RenderOptions(
            user_scope=scope == constants.USER_SCOPE,
            async_rewake_stop=True,
        ),
    )


def _content_current(
    path: Path,
    content: str,
    item: manifest.ManagedHookFile,
    *,
    options: manifest.RenderOptions,
) -> bool:
    """Compare one file through its declared status and merge policy."""

    expected = manifest.render(item, options=options)
    if item.status_policy == "exact":
        return content == expected
    return _merged_content_current(path, content, item, expected=expected)


def _merged_content_current(
    path: Path,
    content: str,
    item: manifest.ManagedHookFile,
    *,
    expected: str,
) -> bool:
    """Compare current content through its declared merge strategy."""

    try:
        return _merged_content(path, content, item, expected=expected) == content
    except (OSError, UnicodeError, ValueError):
        return False


def _merged_content(
    path: Path,
    content: str,
    item: manifest.ManagedHookFile,
    *,
    expected: str,
) -> str:
    """Apply one declared merge strategy for currentness comparison."""

    if item.merge_strategy == "codex-toml":
        return merge.merge_codex_config(content, expected)
    if item.merge_strategy == "claude-json":
        return merge.merge_claude_settings(path, expected)
    return ""


def _scoped_path(root: Path, user_root: Path, scope: str, relative_path: str) -> Path:
    """Return a path below the selected repo or user root."""

    base = user_root if scope == constants.USER_SCOPE else root
    return base / relative_path
