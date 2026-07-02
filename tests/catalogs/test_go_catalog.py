"""Tests Go provider catalog integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.catalogs import catalog as maintainer_catalog
from agent_maintainer.config import loader
from agent_maintainer.core.config import MaintainerConfig


def test_catalog_omits_go_checks_by_default() -> None:
    """Default catalog preserves Python-first behavior."""
    config = MaintainerConfig()
    checks = {
        check.name
        for check in maintainer_catalog.make_checks(
            config,
            "HEAD",
            "origin/main",
        )
    }

    assert "go-format" not in checks
    assert "go-vet" not in checks
    assert "go-test" not in checks


def test_go_fixture_config_produces_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Minimal Go-enabled repo config produces expected checks."""
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.agent_maintainer]
enable_go = true
go_format_command = ["gofmt", "-l", "."]
go_vet_command = ["go", "vet", "./..."]
go_test_command = ["go", "test", "./..."]
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    config = loader.load_config()
    checks = {
        check.name: check
        for check in maintainer_catalog.make_checks(
            config,
            "HEAD",
            "origin/main",
        )
    }

    assert checks["go-format"].command == ["gofmt", "-l", "."]
    assert checks["go-vet"].command == ["go", "vet", "./..."]
    assert checks["go-test"].command == ["go", "test", "./..."]
