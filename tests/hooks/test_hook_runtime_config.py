"""Tests hook runtime repository configuration detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agent_maintainer.hooks import runtime


def test_unreadable_pyproject_is_unconfigured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unreadable config files do not activate global hooks."""

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.agent_maintainer]\n", encoding="utf-8")
    original_read_text = Path.read_text

    def raise_for_pyproject(
        self: Path,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        if self == pyproject:
            raise OSError("permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", raise_for_pyproject)

    assert not runtime.maintainer_configured(tmp_path)
