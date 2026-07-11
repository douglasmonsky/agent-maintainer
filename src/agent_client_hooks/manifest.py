"""Authoritative managed-file inventory for supported agent clients."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from agent_client_hooks import constants, templates

FileKind = Literal["config", "script"]
MergeStrategy = Literal["replace", "codex-toml", "claude-json"]
StatusPolicy = Literal["exact", "merged"]
CONFIG_KIND: FileKind = "config"
SCRIPT_KIND: FileKind = "script"


@dataclass(frozen=True)
class RenderOptions:
    """Variant controls for one managed hook rendering."""

    user_scope: bool = False
    async_rewake_stop: bool = False


Renderer = Callable[[RenderOptions], str]


@dataclass(frozen=True)
class ManagedHookFile:
    """Ownership and lifecycle policy for one managed client file."""

    client: str
    relative_path: str
    description: str
    kind: FileKind
    scopes: tuple[str, ...]
    renderer: Renderer
    merge_strategy: MergeStrategy = "replace"
    ownership_marker: str = "Agent Maintainer"
    status_policy: StatusPolicy = "exact"
    scaffold: bool = True
    uninstall: bool = True
    scaffold_renderer: Renderer | None = None


def managed_files(
    client: str | None = None,
    *,
    scope: str | None = None,
) -> tuple[ManagedHookFile, ...]:
    """Return managed files filtered by client and installation scope."""

    return tuple(
        managed_file
        for managed_file in MANAGED_HOOK_FILES
        if (client is None or managed_file.client == client)
        and (scope is None or scope in managed_file.scopes)
    )


def config_files(client: str) -> tuple[ManagedHookFile, ...]:
    """Return configuration records for one client."""

    return tuple(item for item in managed_files(client) if item.kind == CONFIG_KIND)


def hook_files(client: str) -> tuple[ManagedHookFile, ...]:
    """Return repo-local hook-script records for one client."""

    return tuple(item for item in managed_files(client) if item.kind == SCRIPT_KIND)


def scaffold_files() -> tuple[ManagedHookFile, ...]:
    """Return manifest entries emitted by agent-aware initialization."""

    return tuple(item for item in MANAGED_HOOK_FILES if item.scaffold)


def render(
    managed_file: ManagedHookFile,
    *,
    options: RenderOptions | None = None,
) -> str:
    """Render one managed file for installation."""

    return managed_file.renderer(options or RenderOptions())


def render_scaffold(managed_file: ManagedHookFile) -> str:
    """Render one managed file for a new repository scaffold."""

    renderer = managed_file.scaffold_renderer or managed_file.renderer
    return renderer(RenderOptions())


def _codex_config(options: RenderOptions) -> str:
    return templates.codex_config_block(user_scope=options.user_scope)


def _codex_scaffold(options: RenderOptions) -> str:
    return templates.codex_config_file(user_scope=options.user_scope)


def _codex_post(_options: RenderOptions) -> str:
    return templates.codex_post_hook()


def _codex_pr_wait(_options: RenderOptions) -> str:
    return templates.codex_pr_wait_hook()


def _codex_stop(_options: RenderOptions) -> str:
    return templates.codex_stop_hook()


def _codex_audit(_options: RenderOptions) -> str:
    return templates.hook_audit_shim()


def _claude_config(options: RenderOptions) -> str:
    return templates.claude_settings(
        user_scope=options.user_scope,
        async_rewake_stop=options.async_rewake_stop,
    )


def _claude_post(_options: RenderOptions) -> str:
    return templates.claude_post_hook()


def _claude_pr_wait(_options: RenderOptions) -> str:
    return templates.claude_pr_wait_hook()


def _claude_stop(options: RenderOptions) -> str:
    return templates.claude_stop_hook(async_rewake=options.async_rewake_stop)


def _claude_subagent_stop(options: RenderOptions) -> str:
    return templates.claude_subagent_stop_hook(async_rewake=options.async_rewake_stop)


REPO_SCOPE = (constants.REPO_SCOPE,)
ALL_SCOPES = constants.SCOPES

MANAGED_HOOK_FILES = (
    ManagedHookFile(
        client=constants.CODEX_CLIENT,
        relative_path=".codex/config.toml",
        description="Codex hook config",
        kind=CONFIG_KIND,
        scopes=ALL_SCOPES,
        renderer=_codex_config,
        merge_strategy="codex-toml",
        ownership_marker=templates.CODEX_MARKER,
        status_policy="merged",
        scaffold_renderer=_codex_scaffold,
    ),
    ManagedHookFile(
        constants.CODEX_CLIENT,
        templates.CODEX_POST_HOOK,
        "Codex post-edit hook",
        SCRIPT_KIND,
        REPO_SCOPE,
        _codex_post,
    ),
    ManagedHookFile(
        constants.CODEX_CLIENT,
        templates.CODEX_PR_WAIT_HOOK,
        "Codex PR wait hook",
        SCRIPT_KIND,
        REPO_SCOPE,
        _codex_pr_wait,
    ),
    ManagedHookFile(
        constants.CODEX_CLIENT,
        templates.CODEX_STOP_HOOK,
        "Codex stop hook",
        SCRIPT_KIND,
        REPO_SCOPE,
        _codex_stop,
    ),
    ManagedHookFile(
        constants.CODEX_CLIENT,
        ".codex/hooks/hook_audit.py",
        "Codex hook-audit compatibility shim",
        SCRIPT_KIND,
        REPO_SCOPE,
        _codex_audit,
    ),
    ManagedHookFile(
        client=constants.CLAUDE_CODE_CLIENT,
        relative_path=".claude/settings.json",
        description="Claude Code hook settings",
        kind=CONFIG_KIND,
        scopes=ALL_SCOPES,
        renderer=_claude_config,
        merge_strategy="claude-json",
        ownership_marker=templates.MANAGED_PREFIX,
        status_policy="merged",
    ),
    ManagedHookFile(
        constants.CLAUDE_CODE_CLIENT,
        templates.CLAUDE_POST_HOOK,
        "Claude Code post-edit hook",
        SCRIPT_KIND,
        REPO_SCOPE,
        _claude_post,
    ),
    ManagedHookFile(
        constants.CLAUDE_CODE_CLIENT,
        templates.CLAUDE_PR_WAIT_HOOK,
        "Claude Code PR wait hook",
        SCRIPT_KIND,
        REPO_SCOPE,
        _claude_pr_wait,
    ),
    ManagedHookFile(
        constants.CLAUDE_CODE_CLIENT,
        templates.CLAUDE_STOP_HOOK,
        "Claude Code stop hook",
        SCRIPT_KIND,
        REPO_SCOPE,
        _claude_stop,
    ),
    ManagedHookFile(
        constants.CLAUDE_CODE_CLIENT,
        templates.CLAUDE_SUBAGENT_STOP_HOOK,
        "Claude Code subagent stop hook",
        SCRIPT_KIND,
        REPO_SCOPE,
        _claude_subagent_stop,
    ),
)
