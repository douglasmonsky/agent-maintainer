"""Repository-confined checked-in Gradle wrapper resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent_maintainer.ecosystems.java.errors import JavaConfigurationError

WrapperPlatform = Literal["posix", "windows"]


class GradleWrapperError(JavaConfigurationError, ValueError):
    """Raised when a configured Gradle wrapper is absent or unsafe."""


@dataclass(frozen=True)
class ResolvedGradleWrapper:
    """Canonical wrapper executable and its repository-owned working root."""

    workspace: Path
    gradle_root: Path
    executable: Path


def resolve_gradle_wrapper(
    workspace: Path,
    gradle_root: str,
    *,
    platform: WrapperPlatform | None = None,
) -> ResolvedGradleWrapper:
    """Resolve a checked-in wrapper without consulting PATH."""

    canonical_workspace = workspace.resolve(strict=True)
    canonical_root = _resolve_gradle_root(canonical_workspace, gradle_root)
    selected_platform = _selected_platform(platform)
    canonical_wrapper = _resolve_wrapper(canonical_root, selected_platform)
    return ResolvedGradleWrapper(
        workspace=canonical_workspace,
        gradle_root=canonical_root,
        executable=canonical_wrapper,
    )


def _resolve_gradle_root(workspace: Path, gradle_root: str) -> Path:
    canonical_root = (workspace / gradle_root).resolve(strict=False)
    if not canonical_root.is_relative_to(workspace):
        raise GradleWrapperError("gradle_root escapes repository")
    if not canonical_root.is_dir():
        raise GradleWrapperError("gradle_root is not an existing directory")
    return canonical_root


def _selected_platform(platform: WrapperPlatform | None) -> WrapperPlatform:
    if platform is not None:
        return platform
    return "windows" if os.name == "nt" else "posix"


def _resolve_wrapper(root: Path, platform: WrapperPlatform) -> Path:
    wrapper_name = "gradlew.bat" if platform == "windows" else "gradlew"
    wrapper = root / wrapper_name
    if not wrapper.exists():
        raise GradleWrapperError("checked-in Gradle wrapper is missing")
    canonical_wrapper = wrapper.resolve(strict=True)
    _validate_wrapper(canonical_wrapper, root, platform)
    return canonical_wrapper


def _validate_wrapper(wrapper: Path, root: Path, platform: WrapperPlatform) -> None:
    if not wrapper.is_relative_to(root):
        raise GradleWrapperError("wrapper escapes gradle_root")
    if not wrapper.is_file():
        raise GradleWrapperError("wrapper must be a regular file")
    if platform == "posix" and not os.access(wrapper, os.X_OK):
        raise GradleWrapperError("wrapper is not executable")
