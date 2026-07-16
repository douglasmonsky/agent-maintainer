"""Repository-confined checked-in Gradle wrapper resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

WrapperPlatform = Literal["posix", "windows"]


class GradleWrapperError(ValueError):
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
    canonical_root = (canonical_workspace / gradle_root).resolve(strict=False)
    if not canonical_root.is_relative_to(canonical_workspace):
        raise GradleWrapperError("gradle_root escapes repository")
    if not canonical_root.is_dir():
        raise GradleWrapperError("gradle_root is not an existing directory")
    selected_platform = platform or ("windows" if os.name == "nt" else "posix")
    wrapper_name = "gradlew.bat" if selected_platform == "windows" else "gradlew"
    wrapper = canonical_root / wrapper_name
    if not wrapper.exists():
        raise GradleWrapperError("checked-in Gradle wrapper is missing")
    canonical_wrapper = wrapper.resolve(strict=True)
    if not canonical_wrapper.is_relative_to(canonical_root):
        raise GradleWrapperError("wrapper escapes gradle_root")
    if not canonical_wrapper.is_file():
        raise GradleWrapperError("wrapper must be a regular file")
    if selected_platform == "posix" and not os.access(canonical_wrapper, os.X_OK):
        raise GradleWrapperError("wrapper is not executable")
    return ResolvedGradleWrapper(
        workspace=canonical_workspace,
        gradle_root=canonical_root,
        executable=canonical_wrapper,
    )
