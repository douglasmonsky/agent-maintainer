"""Tests Technical Debt Score assessment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.assess import cli
from agent_maintainer.assess.debt_score import DEBT_SCORE_JSON, DEBT_SCORE_MARKDOWN


def test_debt_score_cli_writes_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Debt score command writes JSON and Markdown artifacts by default."""
    write_repo(tmp_path)

    status = cli.main(["debt", "--target", str(tmp_path), "--json"])

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["score"] >= 0
    assert payload["risk"] in {"low", "moderate", "high", "critical"}
    assert {category["name"] for category in payload["categories"]} >= {
        "Reviewability",
        "Tests and Coverage",
        "Architecture Boundaries",
    }
    assert (tmp_path / ".verify-logs" / DEBT_SCORE_JSON).exists()
    assert (tmp_path / ".verify-logs" / DEBT_SCORE_MARKDOWN).exists()


def test_debt_score_no_write_skips_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Debt score can render without writing diagnostics."""
    write_repo(tmp_path)

    status = cli.main(["debt", "--target", str(tmp_path), "--no-write"])

    assert status == 0
    assert "Technical Debt Score" in capsys.readouterr().out
    assert not (tmp_path / ".verify-logs" / DEBT_SCORE_JSON).exists()


def write_repo(root: Path) -> None:
    """Write a minimal Python repo fixture."""
    (root / "pyproject.toml").write_text(
        """
[tool.agent_maintainer]
mode = "custom"
require_tests = true
coverage_fail_under = 85
diagnostic_artifacts_enabled = true
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
