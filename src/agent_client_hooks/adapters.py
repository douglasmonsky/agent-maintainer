"""Agent client hook adapter contracts and implementations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agent_client_hooks import constants, manifest
from agent_client_hooks import status as hook_statuses

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
    async_rewake_stop: bool = False


HookClientStatus = hook_statuses.HookClientStatus


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

    def install(
        self,
        target: Path,
        scope: str,
    ) -> tuple[PlannedWrite, ...]:
        """Return planned writes for target and scope."""
        raise NotImplementedError

    def uninstall(self, target: Path, scope: str) -> tuple[Path, ...]:
        """Return paths that an uninstall operation would remove."""
        raise NotImplementedError


@dataclass(frozen=True)
class CodexAdapter:
    """Managed hook adapter for Codex."""

    name: str = CODEX_CLIENT

    @property
    def config_paths(self) -> tuple[str, ...]:
        """Return manifest-owned Codex configuration paths."""

        return _manifest_paths(self.name, kind="config")

    @property
    def hook_paths(self) -> tuple[str, ...]:
        """Return manifest-owned Codex hook paths."""

        return _manifest_paths(self.name, kind="script")

    def status(self, target: Path, scope: str) -> HookClientStatus:
        """Return Codex hook install status."""
        return hook_status(self, target, scope)

    def install(
        self,
        target: Path,
        scope: str,
    ) -> tuple[PlannedWrite, ...]:
        """Return Codex hook installation writes."""
        return _install_plans(
            self.name,
            target,
            scope,
            options=manifest.RenderOptions(user_scope=scope == USER_SCOPE),
        )

    def uninstall(self, target: Path, scope: str) -> tuple[Path, ...]:
        """Return Codex hook files managed by Agent Maintainer."""
        return _uninstall_paths(self.name, target, scope)


@dataclass(frozen=True)
class ClaudeCodeAdapter:
    """Managed hook adapter for Claude Code."""

    name: str = CLAUDE_CODE_CLIENT

    @property
    def config_paths(self) -> tuple[str, ...]:
        """Return manifest-owned Claude Code configuration paths."""

        return _manifest_paths(self.name, kind="config")

    @property
    def hook_paths(self) -> tuple[str, ...]:
        """Return manifest-owned Claude Code hook paths."""

        return _manifest_paths(self.name, kind="script")

    def status(self, target: Path, scope: str) -> HookClientStatus:
        """Return Claude Code hook install status."""
        return hook_status(self, target, scope)

    def install(
        self,
        target: Path,
        scope: str,
        *,
        async_rewake_stop: bool = False,
    ) -> tuple[PlannedWrite, ...]:
        """Return Claude Code hook installation writes."""
        options = manifest.RenderOptions(
            user_scope=scope == USER_SCOPE,
            async_rewake_stop=async_rewake_stop,
        )
        return _install_plans(self.name, target, scope, options=options)

    def uninstall(self, target: Path, scope: str) -> tuple[Path, ...]:
        """Return Claude Code hook files managed by Agent Maintainer."""
        return _uninstall_paths(self.name, target, scope)


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
    return hook_statuses.client_status(
        adapter.name,
        target,
        scope,
        user_root=home(),
    )


def _manifest_paths(client: str, *, kind: manifest.FileKind) -> tuple[str, ...]:
    """Return manifest paths of one kind for a client."""

    return tuple(item.relative_path for item in manifest.managed_files(client) if item.kind == kind)


def _install_plans(
    client: str,
    target: Path,
    scope: str,
    *,
    options: manifest.RenderOptions,
) -> tuple[PlannedWrite, ...]:
    """Build install writes from the authoritative client manifest."""

    root = target.resolve()
    return tuple(
        PlannedWrite(
            path=scoped_path(root, scope, item.relative_path),
            content=manifest.render(item, options=options),
            description=_plan_description(item, options=options),
            merge_json=item.merge_strategy == "claude-json",
            merge_codex=item.merge_strategy == "codex-toml",
        )
        for item in manifest.managed_files(client, scope=scope)
    )


def _plan_description(
    item: manifest.ManagedHookFile,
    *,
    options: manifest.RenderOptions,
) -> str:
    """Return a variant-aware install description."""

    if item.client == CLAUDE_CODE_CLIENT and item.kind == "config" and options.async_rewake_stop:
        return f"{item.description} (async rewake Stop/SubagentStop)"
    return item.description


def _uninstall_paths(client: str, target: Path, scope: str) -> tuple[Path, ...]:
    """Return only manifest files owned in the selected scope."""

    root = target.resolve()
    return tuple(
        scoped_path(root, scope, item.relative_path)
        for item in manifest.managed_files(client, scope=scope)
        if item.uninstall
    )


def scoped_path(root: Path, scope: str, relative_path: str) -> Path:
    """Return repo or user scoped hook path."""
    if scope == USER_SCOPE:
        return home() / relative_path
    return root / relative_path


def home() -> Path:
    """Return user's home directory."""
    return Path.home()
