"""Tests for Bandit JSON artifact generation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.runners import bandit as run_bandit
from tests.support.callbacks import constant_callback

INVALID_CONFIG_EXIT_CODE = 2


def test_bandit_command_uses_root_policy_when_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass the conventional root .bandit file even when source roots are narrower."""
    (tmp_path / ".bandit").write_text("[bandit]\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    command = run_bandit.bandit_command("bandit", package_paths=("src",))

    assert command == ["bandit", "-q", "-f", "json", "--ini", ".bandit", "-r", "src"]


def test_run_bandit_writes_json_artifact_and_prints_compact_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    json_path = tmp_path / "bandit.json"

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert "-f" in command
        assert "json" in command
        assert command[-2:] == ["scripts", "src/agent_maintainer"]
        return subprocess.CompletedProcess(
            command,
            1,
            stdout=json.dumps(
                {
                    "results": [
                        None,
                        {
                            "filename": "scripts/example.py",
                            "line_number": 3,
                            "test_id": "B101",
                            "issue_severity": "LOW",
                            "issue_confidence": "HIGH",
                            "issue_text": "Use of assert detected.",
                        },
                    ]
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(run_bandit.shutil, "which", constant_callback("/usr/bin/bandit"))
    monkeypatch.setattr(run_bandit.subprocess, "run", fake_run)

    assert run_bandit.run_bandit(json_path, package_paths=("scripts", "src/agent_maintainer")) == 1

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["results"][1]["test_id"] == "B101"
    assert "scripts/example.py:3: B101 LOW/HIGH Use of assert detected." in capsys.readouterr().out


def test_run_bandit_writes_clean_json_without_printing_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    json_path = tmp_path / "bandit.json"

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout='{"results": []}\n', stderr="")

    monkeypatch.setattr(run_bandit.subprocess, "run", fake_run)

    assert run_bandit.run_bandit(json_path, package_paths=("scripts",)) == 0

    assert json.loads(json_path.read_text(encoding="utf-8"))["results"] == []
    assert capsys.readouterr().out == ""


def test_run_bandit_does_not_preserve_stale_artifact_when_json_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    json_path = tmp_path / "bandit.json"
    json_path.write_text('{"results": []}\n', encoding="utf-8")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            INVALID_CONFIG_EXIT_CODE,
            stdout="not json\n",
            stderr="",
        )

    monkeypatch.setattr(run_bandit.subprocess, "run", fake_run)

    assert run_bandit.run_bandit(json_path, package_paths=("scripts",)) == INVALID_CONFIG_EXIT_CODE

    assert not json_path.exists()
    assert "not json" in capsys.readouterr().out


def test_main_uses_configured_diagnostic_artifact_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnostic_dir = tmp_path / "custom-logs"
    config = MaintainerConfig(
        diagnostic_artifacts_dir=str(diagnostic_dir),
        package_paths=("scripts", "src/agent_maintainer"),
    )
    seen: dict[str, object] = {}

    def fake_run_bandit(json_path: Path, *, package_paths: tuple[str, ...]) -> int:
        seen["json_path"] = json_path
        seen["package_paths"] = package_paths
        return 0

    monkeypatch.setattr(run_bandit, "load_config", lambda: config)
    monkeypatch.setattr(run_bandit, "run_bandit", fake_run_bandit)

    assert run_bandit.main() == 0

    assert seen == {
        "json_path": diagnostic_dir / "bandit.json",
        "package_paths": ("scripts", "src/agent_maintainer"),
    }
