"""Tests DocSync Agent Maintainer catalog integration."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from agent_maintainer.catalogs import catalog as maintainer_catalog
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.models import LOCAL_GATE_PROFILES


def test_catalog_omits_docsync_without_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repositories without DocSync trace do not get a DocSync check."""

    monkeypatch.chdir(tmp_path)

    checks = maintainer_catalog.make_checks(MaintainerConfig(), "HEAD", "origin/main")

    assert "docsync" not in {check.name for check in checks}


def test_catalog_adds_docsync_when_trace_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repositories with a DocSync trace get a structured DocSync check."""

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".docsync").mkdir()
    (tmp_path / ".docsync" / "trace.yml").write_text("version: 1\n", encoding="utf-8")

    checks = {
        check.name: check
        for check in maintainer_catalog.make_checks(
            MaintainerConfig(),
            "origin/main",
            "origin/main",
        )
    }

    docsync = checks["docsync"]
    assert docsync.command == [
        sys.executable,
        "-m",
        "docsync",
        "check",
        "--base",
        "origin/main",
    ]
    assert docsync.profiles == LOCAL_GATE_PROFILES
    assert docsync.required_paths == (".docsync/trace.yml",)
    assert docsync.artifact_paths == (".docsync/out/report.json",)
