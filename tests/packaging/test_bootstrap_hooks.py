"""Tests bootstrap hook reporting behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_guardrails.core import bootstrap as guardrail_bootstrap

INSTALL_STATUS = 12


def test_guardrail_install_runs_hook_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, Path]] = []
    monkeypatch.setattr(guardrail_bootstrap, "project_root", lambda: tmp_path)
    monkeypatch.setattr(
        guardrail_bootstrap,
        "install_pre_commit",
        lambda repo_root: calls.append(("pre-commit", repo_root)) or INSTALL_STATUS,
    )
    monkeypatch.setattr(
        guardrail_bootstrap,
        "report_codex_hooks",
        lambda repo_root: calls.append(("codex-hooks", repo_root)),
    )

    assert guardrail_bootstrap.install() == INSTALL_STATUS
    assert calls == [("pre-commit", tmp_path), ("codex-hooks", tmp_path)]


def test_guardrail_report_codex_hooks_absent_is_quiet(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    guardrail_bootstrap.report_codex_hooks(tmp_path)

    assert capsys.readouterr().out == ""


def test_guardrail_reports_codex_hooks(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("[features]\nhooks = true\n", encoding="utf-8")

    guardrail_bootstrap.report_codex_hooks(tmp_path)

    assert "Codex hooks configured" in capsys.readouterr().out
