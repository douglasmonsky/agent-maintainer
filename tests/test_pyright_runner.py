"""Tests for generated Pyright project configuration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import run_pyright
from scripts.guardrail_config import GuardrailConfig


def test_write_pyright_config_uses_guardrail_mode_and_roots(tmp_path: Path) -> None:
    config = GuardrailConfig(
        package_paths=("scripts", ".codex/hooks"),
        test_roots=("tests",),
        pyright_type_checking_mode="strict",
    )

    path = run_pyright.write_pyright_config(tmp_path, config)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["typeCheckingMode"] == "strict"
    assert payload["include"] == ["scripts", ".codex/hooks", "tests"]


def test_run_pyright_writes_json_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = tmp_path / "pyrightconfig.generated.json"
    config_path.write_text("{}", encoding="utf-8")
    json_path = tmp_path / "pyright.json"

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert "--outputjson" in command
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"summary": {"errorCount": 0}}\n',
            stderr="",
        )

    monkeypatch.setattr(run_pyright.shutil, "which", lambda name: "/usr/bin/pyright")
    monkeypatch.setattr(run_pyright.subprocess, "run", fake_run)

    assert run_pyright.run_pyright(config_path, json_path) == 0

    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["errorCount"] == 0
    assert '"errorCount": 0' in capsys.readouterr().out


def test_main_uses_configured_diagnostic_artifact_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    diagnostic_dir = tmp_path / "custom-logs"
    config = GuardrailConfig(diagnostic_artifacts_dir=str(diagnostic_dir))
    seen_paths: dict[str, Path] = {}

    def fake_run_pyright(config_path: Path, json_path: Path | None) -> int:
        seen_paths["config"] = config_path
        assert json_path is not None
        seen_paths["json"] = json_path
        return 0

    monkeypatch.setattr(run_pyright, "load_config", lambda: config)
    monkeypatch.setattr(run_pyright, "run_pyright", fake_run_pyright)

    assert run_pyright.main() == 0

    assert seen_paths["config"] == diagnostic_dir / "pyrightconfig.generated.json"
    assert seen_paths["json"] == diagnostic_dir / "pyright.json"
    assert seen_paths["config"].exists()


def test_write_json_output_skips_blank_output(tmp_path: Path) -> None:
    path = tmp_path / "pyright.json"

    run_pyright.write_json_output(path, "\n")

    assert not path.exists()
