"""Tests for the Archguard command line interface."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

from archguard import cli as archguard_cli


def test_main_dispatches_tach_config_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Run the Tach config subcommand through the top-level parser."""
    monkeypatch.setattr(archguard_cli, "tach_config_issues", lambda *args, **kwargs: [])

    assert archguard_cli.main(["tach-config", "--strict-root-module"]) == 0

    assert "tach.toml configured" in capsys.readouterr().out


def test_main_dispatches_tach_config_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Print Tach config issues from the Archguard subcommand."""
    monkeypatch.setattr(
        archguard_cli,
        "tach_config_issues",
        lambda *args, **kwargs: ["bad"],
    )

    assert archguard_cli.main(["tach-config"]) == 1

    assert "bad" in capsys.readouterr().out


def test_main_dispatches_decision_check_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Run the decision-check subcommand with explicit policy args."""

    def fake_decision_check_failures(
        repo_root: Path,
        *,
        base_ref: str,
        staged: bool,
        decision_roots: tuple[str, ...],
        policy_patterns: tuple[str, ...],
    ) -> list[str]:
        assert repo_root
        assert base_ref == "HEAD"
        assert staged is True
        assert decision_roots == ("docs/adr",)
        assert policy_patterns == ("tach.toml",)
        return []

    monkeypatch.setattr(
        archguard_cli,
        "decision_check_failures",
        fake_decision_check_failures,
    )

    assert (
        archguard_cli.main(
            [
                "decision-check",
                "--base-ref",
                "HEAD",
                "--staged",
                "--decision-root",
                "docs/adr",
                "--policy-pattern",
                "tach.toml",
            ],
        )
        == 0
    )

    assert "architecture decision notes cover" in capsys.readouterr().out


def test_main_dispatches_decision_check_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Return nonzero when the decision-check gate reports failures."""
    monkeypatch.setattr(
        archguard_cli,
        "decision_check_failures",
        lambda *args, **kwargs: ["missing decision"],
    )

    assert archguard_cli.main(["decision-check"]) == 1

    assert "missing decision" in capsys.readouterr().out


def test_main_dispatches_decision_new(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Create a decision note through the nested decision command."""
    created_path = tmp_path / "docs/adr/2026-06-27-example.md"
    monkeypatch.setattr(
        archguard_cli,
        "new_decision_note",
        lambda *args, **kwargs: created_path,
    )

    assert archguard_cli.main(["decision", "new", "Example", "--decision-root", "docs/adr"]) == 0

    assert str(created_path) in capsys.readouterr().out


def test_console_main_exits_with_main_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """Console entrypoint exits with the delegated result."""
    expected_code = 7
    monkeypatch.setattr(sys, "argv", ["archguard", "tach-config"])
    monkeypatch.setattr(archguard_cli, "main", lambda argv: expected_code)

    with pytest.raises(SystemExit) as exc_info:
        archguard_cli.console_main()

    assert exc_info.value.code == expected_code


def test_module_entrypoint_exits_with_main_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """python -m archguard delegates to archguard.cli.main."""
    expected_code = 5
    monkeypatch.setattr(sys, "argv", ["python -m archguard", "tach-config"])
    monkeypatch.setattr(archguard_cli, "main", lambda argv: expected_code)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("archguard", run_name="__main__")

    assert exc_info.value.code == expected_code


def test_main_dispatches_map(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Run architecture map command through top-level parser."""

    monkeypatch.setattr(archguard_cli, "load_architecture", lambda repo_root: object())
    monkeypatch.setattr(archguard_cli, "render_map", lambda architecture: "mapped")

    assert archguard_cli.main(["map"]) == 0
    assert "mapped" in capsys.readouterr().out


def test_main_dispatches_impact(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Run architecture impact command through top-level parser."""

    monkeypatch.setattr(archguard_cli, "load_architecture", lambda repo_root: object())
    monkeypatch.setattr(
        archguard_cli,
        "render_impact",
        lambda repo_root, architecture, path: f"impact {path}",
    )

    assert archguard_cli.main(["impact", "src/example.py"]) == 0
    assert "impact src/example.py" in capsys.readouterr().out


def test_main_dispatches_explain_boundary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Run boundary explanation command through top-level parser."""

    monkeypatch.setattr(archguard_cli, "load_architecture", lambda repo_root: object())
    monkeypatch.setattr(
        archguard_cli,
        "render_boundary",
        lambda repo_root, architecture, source, target: f"boundary {source} {target}",
    )

    assert archguard_cli.main(["explain-boundary", "src/a.py", "src/b.py"]) == 0
    assert "boundary src/a.py src/b.py" in capsys.readouterr().out
