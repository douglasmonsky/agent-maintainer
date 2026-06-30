"""Tests setup advisor recommendations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.assess import cli
from agent_maintainer.assess.evidence import collect_evidence
from agent_maintainer.assess.setup_advisor import build_setup_report


def test_setup_advisor_recommends_agent_track_for_agent_repo(tmp_path: Path) -> None:
    """Agent assets produce agent track recommendation and setup prompts."""
    write_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("Read local guidance.\n", encoding="utf-8")
    (tmp_path / ".codex" / "hooks").mkdir(parents=True)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)

    report = build_setup_report(collect_evidence(tmp_path))

    assert report.track == "agent"
    assert report.preset == "strict-new-repo"
    assert report.confidence == "high"
    assert any(gate.name == "pip-audit" for gate in report.optional_gates)
    assert any("architecture boundaries" in prompt for prompt in report.agent_prompts)


def test_setup_advisor_json_cli(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Setup advisor CLI renders stable JSON."""
    write_repo(tmp_path)

    status = cli.main(["setup", "--target", str(tmp_path), "--json"])

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["track"] == "core"
    assert payload["preset"] == "strict-new-repo"
    assert payload["evidence"]["has_agent_config"] is True


def write_repo(root: Path) -> None:
    """Write a minimal Python repo fixture."""
    (root / "pyproject.toml").write_text(
        """
[tool.agent_maintainer]
mode = "custom"
""".strip(),
        encoding="utf-8",
    )
    package = root / "src" / "example"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_example.py").write_text(
        "def test_example():\n    assert True\n",
        encoding="utf-8",
    )
