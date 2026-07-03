"""Compatibility facade for Agent Maintainer configuration.

The implementation is split by responsibility:
- `agent_maintainer.config.schema` owns constants and the dataclass.
- `agent_maintainer.config.coercion` owns value coercion.
- `agent_maintainer.config.modes` owns built-in presets.
- `agent_maintainer.config.loader` owns pyproject and environment loading.
"""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.config import loader, modes, schema

load_config = loader.load_config
apply_mode = modes.apply_mode
FRESH_STRICT_MODE = schema.FRESH_STRICT_MODE
IMPORT_LINTER_TOOL = schema.IMPORT_LINTER_TOOL
LEGACY_RATCHET_MODE = schema.LEGACY_RATCHET_MODE
TACH_TOOL = schema.TACH_TOOL
VALID_ARCHITECTURE_TOOLS = schema.VALID_ARCHITECTURE_TOOLS
VALID_MODES = schema.VALID_MODES
MaintainerConfig = schema.MaintainerConfig


def existing_paths(paths: tuple[str, ...]) -> list[str]:
    """Return configured paths that exist in the current working tree."""

    return [path for path in paths if Path(path).exists()]


def any_path_exists(paths: tuple[str, ...]) -> bool:
    """Return whether at least one configured path exists."""

    return any(Path(path).exists() for path in paths)


def format_paths(paths: tuple[str, ...]) -> str:
    """Format configured paths for compact diagnostics."""

    return ", ".join(paths) if paths else "<none>"


def normalize_repo_path(path: str) -> str:
    """Return repository-relative path text without stripping dot directories."""

    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def path_matches_roots(path: str, roots: tuple[str, ...]) -> bool:
    """Return whether a normalized file path belongs to any configured root."""

    normalized = normalize_repo_path(path)
    for root in roots:
        clean_root = normalize_repo_path(root)
        if clean_root in {"", "."}:
            return True
        if normalized == clean_root or normalized.startswith(f"{clean_root}/"):
            return True
    return False
