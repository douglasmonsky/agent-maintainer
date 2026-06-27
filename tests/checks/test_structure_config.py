"""Tests structure cohesion config and catalog wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.catalogs import catalog as maintainer_catalog
from agent_maintainer.core import config as maintainer_config
from agent_maintainer.core.config import MaintainerConfig

WARN_THRESHOLD = 12
BLOCK_THRESHOLD = 34
CLUSTER_MIN = 3


def test_structure_config_loads_thresholds_and_patterns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.agent_maintainer]
folder_file_warn = 12
folder_file_block = 34
structure_cluster_min = 3
structure_paths = ["scripts"]
structure_ignore_paths = ["tests/**"]
structure_hint_patterns = ["^domain_"]
""",
        encoding="utf-8",
    )

    config = maintainer_config.load_config()

    assert config.folder_file_warn == WARN_THRESHOLD
    assert config.folder_file_block == BLOCK_THRESHOLD
    assert config.structure_cluster_min == CLUSTER_MIN
    assert config.structure_paths == ("scripts",)
    assert config.structure_ignore_paths == ("tests/**",)
    assert config.structure_hint_patterns == ("^domain_",)


def test_structure_check_is_in_catalog_and_blocks_only_fresh_strict() -> None:
    custom = MaintainerConfig(source_roots=("scripts",), folder_file_block=BLOCK_THRESHOLD)
    strict = MaintainerConfig(
        mode="fresh-strict",
        source_roots=("scripts",),
        folder_file_block=BLOCK_THRESHOLD,
    )

    custom_check = next(
        check
        for check in maintainer_catalog.make_checks(custom, "HEAD", "origin/main")
        if check.name == "structure-cohesion"
    )
    strict_check = next(
        check
        for check in maintainer_catalog.make_checks(strict, "HEAD", "origin/main")
        if check.name == "structure-cohesion"
    )

    assert custom_check.report_success_output is True
    assert "--block-threshold" in custom_check.command
    assert "0" in custom_check.command
    assert str(BLOCK_THRESHOLD) in strict_check.command
    assert strict_check.required_paths == ()
