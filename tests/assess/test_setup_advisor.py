"""Tests setup advisor recommendations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.assess import cli
from agent_maintainer.assess.evidence import collect_evidence
from agent_maintainer.assess.setup_advisor import build_setup_report

MANY_SOURCE_FILES = 45
AGENT_HEAVY_FILES = 25


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


def test_setup_advisor_recommends_hardening_track(tmp_path: Path) -> None:
    """CI plus config files can justify the hardening track."""

    write_repo(tmp_path)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "verify.yml").write_text(
        "name: verify\n",
        encoding="utf-8",
    )
    (tmp_path / "config.yml").write_text("enabled: true\n", encoding="utf-8")

    report = build_setup_report(collect_evidence(tmp_path))

    assert report.track == "hardening"
    assert any(gate.name == "yamllint" for gate in report.optional_gates)


def test_setup_advisor_recommends_legacy_ratchet(tmp_path: Path) -> None:
    """Large untested repos should start with legacy-ratchet adoption."""

    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'legacy'\n",
        encoding="utf-8",
    )
    package = tmp_path / "src" / "legacy"
    package.mkdir(parents=True)
    for index in range(MANY_SOURCE_FILES):
        (package / f"module_{index}.py").write_text("VALUE = 1\n", encoding="utf-8")

    report = build_setup_report(collect_evidence(tmp_path))

    assert report.track == "core"
    assert report.preset == "legacy-ratchet"
    assert any("No test tree" in reason for reason in report.reasons)
    assert any("smallest behavior surface" in prompt for prompt in report.agent_prompts)


def test_setup_advisor_recommends_agent_heavy_preset(tmp_path: Path) -> None:
    """Mature agent repos can get the ai-agent-heavy preset."""

    write_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("Read local guidance.\n", encoding="utf-8")
    package = tmp_path / "src" / "example"
    tests = tmp_path / "tests"
    for index in range(AGENT_HEAVY_FILES):
        (package / f"module_{index}.py").write_text("VALUE = 1\n", encoding="utf-8")
        (tests / f"test_module_{index}.py").write_text(
            "def test_value():\n    assert True\n",
            encoding="utf-8",
        )

    report = build_setup_report(collect_evidence(tmp_path))

    assert report.track == "agent"
    assert report.preset == "ai-agent-heavy"


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
