"""Public verification-plan command tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_maintainer.verification_plan import cli
from agent_maintainer.verification_plan.models import VerificationPlanReport

USAGE_ERROR = 2


def test_enforcement_changes_only_exit_status(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = _report(blockers=("architecture/adr: Add an ADR.",))
    monkeypatch.setattr(cli, "build_verification_plan", lambda *args, **kwargs: report)

    assert cli.main(["--json"]) == 0
    first = capsys.readouterr().out
    assert cli.main(["--json", "--enforce"]) == 1
    second = capsys.readouterr().out

    assert first == second
    assert json.loads(first)["blocking_findings"] == [
        "architecture/adr: Add an ADR.",
    ]


def test_text_and_json_success_use_requested_arguments(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    calls: list[tuple[Path, str, bool, Path]] = []

    def build(
        target: Path,
        *,
        base_ref: str,
        staged: bool,
        policy_path: Path,
    ) -> VerificationPlanReport:
        calls.append((target, base_ref, staged, policy_path))
        return _report()

    monkeypatch.setattr(cli, "build_verification_plan", build)

    assert cli.main(["--target", str(tmp_path), "--base-ref", "dev"]) == 0
    assert "Ready:" in capsys.readouterr().out
    assert cli.main(["--staged", "--policy", "custom.toml", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["schema_version"] == 1
    assert calls == [
        (tmp_path, "dev", False, Path(".agent-maintainer/path-risk.toml")),
        (Path("."), "origin/main", True, Path("custom.toml")),
    ]


@pytest.mark.parametrize(
    "error",
    (
        RuntimeError("Could not resolve base ref 'missing'"),
        cli.PolicyError("invalid policy"),
    ),
)
def test_expected_failures_return_usage_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    def fail(*args: object, **kwargs: object) -> VerificationPlanReport:
        del args, kwargs
        raise error

    monkeypatch.setattr(cli, "build_verification_plan", fail)

    assert cli.main([]) == USAGE_ERROR
    assert capsys.readouterr().err == f"FAIL verify-plan: {error}\n"


def test_absent_policy_in_synthetic_git_repository_is_valid(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _git(tmp_path, "init")
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(
        tmp_path,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-m",
        "initial",
    )

    assert cli.main(["--target", str(tmp_path), "--base-ref", "HEAD", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["policy_configured"] is False
    assert payload["changes"] == []


def _report(*, blockers: tuple[str, ...] = ()) -> VerificationPlanReport:
    return VerificationPlanReport(
        target="/repo",
        base_ref="main",
        staged=False,
        policy_path="policy.toml",
        policy_configured=True,
        blocking_findings=blockers,
    )


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
