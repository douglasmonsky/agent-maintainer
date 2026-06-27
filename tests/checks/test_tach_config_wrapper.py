"""Tests for Agent Maintainer Tach compatibility shims."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer import tach as maintainer_tach


def test_agent_maintainer_tach_delegates_to_archguard_tach_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the temporary Agent Maintainer Tach facade working."""

    def fake_tach_config_issues(repo_root: Path, *, require_strict_root: bool) -> list[str]:
        assert repo_root == tmp_path
        assert require_strict_root is True
        return ["bad"]

    monkeypatch.setattr(
        maintainer_tach,
        "archguard_tach_config_issues",
        fake_tach_config_issues,
    )

    assert maintainer_tach.tach_config_issues(tmp_path, require_strict_root=True) == ["bad"]
