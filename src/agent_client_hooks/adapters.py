"""Agent client hook adapter contracts and implementations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agent_client_hooks import constants, templates

ALL_CLIENTS = constants.ALL_CLIENTS
CLAUDE_CODE_CLIENT = constants.CLAUDE_CODE_CLIENT
CLIENTS = constants.CLIENTS
CODEX_CLIENT = constants.CODEX_CLIENT
REPO_SCOPE = constants.REPO_SCOPE
SCOPES = constants.SCOPES
USER_SCOPE = constants.USER_SCOPE


@dataclass(frozen=True)
class PlannedWrite:
    """One file planned for hook installation."""

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


@dataclass(frozen=True)
class HookClientStatus:
    """Computed status for one managed agent client."""

    name: str
    config_present: bool
    scripts_present: bool


class AgentClientAdapter(Protocol):
    """Protocol implemented by supported agent hook clients."""

    @property
    def name(self) -> str:
        """Return stable client identifier."""
        raise NotImplementedError

    @property
    def config_paths(self) -> tuple[str, ...]:
        """Return managed config paths relative to repo or home."""
        raise NotImplementedError

    @property
    def hook_paths(self) -> tuple[str, ...]:
        """Return managed hook script paths relative to repo or home."""
        raise NotImplementedError

    def status(self, target: Path, scope: str) -> HookClientStatus:
        """Return current install status for target and scope."""
        raise NotImplementedError

    def install(self, target: Path, scope: str) -> tuple[PlannedWrite, ...]:
        """Return planned writes for target and scope."""
        raise NotImplementedError

    def uninstall(self, target: Path, scope: str) -> tuple[Path, ...]:
        """Return paths that an uninstall operation would remove."""
        raise NotImplementedError


@dataclass(frozen=True)
class CodexAdapter:
    """Managed hook adapter for Codex."""

    name: str = CODEX_CLIENT
    config_paths: tuple[str, ...] = (".codex/config.toml",)
    hook_paths: tuple[str, ...] = (
        templates.CODEX_POST_HOOK,
        templates.CODEX_STOP_HOOK,
    )

    def status(self, target: Path, scope: str) -> HookClientStatus:
        """Return Codex hook install status."""
        return hook_status(self, target, scope)

    def install(self, target: Path, scope: str) -> tuple[PlannedWrite, ...]:
        """Return Codex hook installation writes."""
        root = target.resolve()
        plans = (
            PlannedWrite(
                scoped_path(root, scope, self.config_paths[0]),
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
                root / templates.CODEX_STOP_HOOK, templates.codex_stop_hook(), "Codex stop hook"
            ),
            PlannedWrite(
                root / ".codex/hooks/hook_audit.py",
                templates.hook_audit_shim(),
                "Codex hook-audit compatibility shim",
            ),
        )

    def uninstall(self, target: Path, scope: str) -> tuple[Path, ...]:
        """Return Codex hook files managed by Agent Maintainer."""
        root = target.resolve()
        return (
            scoped_path(root, scope, self.config_paths[0]),
            *(scoped_path(root, scope, hook_path) for hook_path in self.hook_paths),
        )


@dataclass(frozen=True)
class ClaudeCodeAdapter:
    """Managed hook adapter for Claude Code."""

    name: str = CLAUDE_CODE_CLIENT
    config_paths: tuple[str, ...] = (".claude/settings.json",)
    hook_paths: tuple[str, ...] = (
        templates.CLAUDE_POST_HOOK,
        templates.CLAUDE_STOP_HOOK,
        templates.CLAUDE_SUBAGENT_STOP_HOOK,
    )

    def status(self, target: Path, scope: str) -> HookClientStatus:
        """Return Claude Code hook install status."""
        return hook_status(self, target, scope)

    def install(self, target: Path, scope: str) -> tuple[PlannedWrite, ...]:
        """Return Claude Code hook installation writes."""
        root = target.resolve()
        plans = (
            PlannedWrite(
                scoped_path(root, scope, self.config_paths[0]),
                templates.claude_settings(user_scope=scope == USER_SCOPE),
                "Claude Code hook settings",
                merge_json=True,
            ),
        )
        if scope == USER_SCOPE:
            return plans
        return (
            *plans,
            PlannedWrite(
                root / templates.CLAUDE_POST_HOOK,
                templates.claude_post_hook(),
                "Claude Code post-edit hook",
            ),
            PlannedWrite(
                root / templates.CLAUDE_STOP_HOOK,
                templates.claude_stop_hook(),
                "Claude Code stop hook",
            ),
            PlannedWrite(
                root / templates.CLAUDE_SUBAGENT_STOP_HOOK,
                templates.claude_subagent_stop_hook(),
                "Claude Code subagent stop hook",
            ),
        )

    def uninstall(self, target: Path, scope: str) -> tuple[Path, ...]:
        """Return Claude Code hook files managed by Agent Maintainer."""
        root = target.resolve()
        return (
            scoped_path(root, scope, self.config_paths[0]),
            *(scoped_path(root, scope, hook_path) for hook_path in self.hook_paths),
        )


def selected_clients(client: str) -> tuple[str, ...]:
    """Return concrete clients selected by CLI value."""
    if client == ALL_CLIENTS:
        return CLIENTS
    return (client,)


def adapter_for_client(client: str) -> AgentClientAdapter:
    """Return adapter for supported agent client."""
    adapters = {adapter.name: adapter for adapter in client_adapters()}
    try:
        return adapters[client]
    except KeyError as exc:
        msg = f"Unsupported hook client: {client}"
        raise ValueError(msg) from exc


def client_adapters() -> tuple[AgentClientAdapter, ...]:
    """Return supported agent client adapters."""
    return (CodexAdapter(), ClaudeCodeAdapter())


def config_file(client: str, root: Path, scope: str) -> Path:
    """Return config file path for one client."""
    adapter = adapter_for_client(client)
    return scoped_path(root, scope, adapter.config_paths[0])


def hook_script_paths(client: str, root: Path, scope: str) -> tuple[Path, ...]:
    """Return expected hook script paths for one client."""
    adapter = adapter_for_client(client)
    return tuple(scoped_path(root, scope, hook_path) for hook_path in adapter.hook_paths)


def hook_status(adapter: AgentClientAdapter, target: Path, scope: str) -> HookClientStatus:
    """Return compact install status for adapter."""
    root = target.resolve()
    config_present = all(
        scoped_path(root, scope, config_path).exists() for config_path in adapter.config_paths
    )
    scripts_present = all(
        scoped_path(root, scope, hook_path).exists() for hook_path in adapter.hook_paths
    )
    return HookClientStatus(adapter.name, config_present, scripts_present)


def scoped_path(root: Path, scope: str, relative_path: str) -> Path:
    """Return repo or user scoped hook path."""
    if scope == USER_SCOPE:
        return home() / relative_path
    return root / relative_path


def home() -> Path:
    """Return user's home directory."""
    return Path.home()
