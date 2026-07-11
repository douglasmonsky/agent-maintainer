"""Tests for Ruff JSON artifact generation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.runners import ruff as run_ruff
from tests.support.callbacks import constant_callback

INVALID_CONFIG_EXIT_CODE = 2


def test_run_ruff_writes_json_artifact_and_prints_compact_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    json_path = tmp_path / "ruff.json"

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert "--output-format=json" in command
        assert "lint.mccabe.max-complexity=7" in command
        return subprocess.CompletedProcess(
            command,
            1,
            stdout=json.dumps(
                [
                    None,
                    {
                        "filename": "scripts/example.py",
                        "location": {"row": 2, "column": 3},
                        "code": "F401",
                        "message": "`os` imported but unused",
                    },
                ]
            ),
            stderr="",
        )

    monkeypatch.setattr(run_ruff.shutil, "which", constant_callback("/usr/bin/ruff"))
    monkeypatch.setattr(run_ruff.subprocess, "run", fake_run)

    assert run_ruff.run_ruff(json_path, max_complexity=7) == 1

    assert json.loads(json_path.read_text(encoding="utf-8"))[1]["code"] == "F401"
    assert "scripts/example.py:2:3: F401 `os` imported but unused" in capsys.readouterr().out


def test_run_ruff_writes_clean_json_without_printing_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    json_path = tmp_path / "ruff.json"

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="[]\n", stderr="")

    monkeypatch.setattr(run_ruff.subprocess, "run", fake_run)

    assert run_ruff.run_ruff(json_path, max_complexity=8) == 0

    assert json.loads(json_path.read_text(encoding="utf-8")) == []
    assert capsys.readouterr().out == ""


def test_run_ruff_does_not_preserve_stale_artifact_when_json_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    json_path = tmp_path / "ruff.json"
    json_path.write_text("[]\n", encoding="utf-8")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            INVALID_CONFIG_EXIT_CODE,
            stdout="not json\n",
            stderr="",
        )

    monkeypatch.setattr(run_ruff.subprocess, "run", fake_run)

    assert run_ruff.run_ruff(json_path, max_complexity=8) == INVALID_CONFIG_EXIT_CODE

    assert not json_path.exists()
    assert "not json" in capsys.readouterr().out


def test_main_uses_configured_diagnostic_artifact_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnostic_dir = tmp_path / "custom-logs"
    config = MaintainerConfig(
        diagnostic_artifacts_dir=str(diagnostic_dir),
        ruff_max_complexity=6,
    )
    seen: dict[str, object] = {}

    def fake_run_ruff(json_path: Path, *, max_complexity: int) -> int:
        seen["json_path"] = json_path
        seen["max_complexity"] = max_complexity
        return 0

    monkeypatch.setattr(run_ruff, "load_config", lambda: config)
    monkeypatch.setattr(run_ruff, "run_ruff", fake_run_ruff)

    assert run_ruff.main() == 0

    assert seen == {
        "json_path": diagnostic_dir / "ruff.json",
        "max_complexity": 6,
    }
