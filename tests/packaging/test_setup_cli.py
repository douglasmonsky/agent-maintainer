"""Tests side-effect-safe bootstrap and install argument parsing."""

import os
import subprocess  # nosec B404
import sys
from pathlib import Path

import pytest

from agent_maintainer.core import bootstrap, setup_cli
from tests.support.paths import REPO_ROOT

BOOTSTRAP_STATUS = 17
INSTALL_STATUS = 19
ARGUMENT_ERROR_STATUS = 2


def test_setup_parsers_forward_explicit_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parsed setup options reach the selected operation exactly once."""

    calls: list[tuple[str, dict[str, object]]] = []

    def record_bootstrap(*, target: Path | None = None, dry_run: bool = False) -> int:
        calls.append(("bootstrap", {"target": target, "dry_run": dry_run}))
        return BOOTSTRAP_STATUS

    def record_install(
        *,
        target: Path | None = None,
        dry_run: bool = False,
        force: bool = False,
    ) -> int:
        calls.append(
            (
                "install",
                {"target": target, "dry_run": dry_run, "force": force},
            )
        )
        return INSTALL_STATUS

    monkeypatch.setattr(
        setup_cli.setup,
        "bootstrap",
        record_bootstrap,
    )
    monkeypatch.setattr(
        setup_cli.setup,
        "install",
        record_install,
    )

    assert setup_cli.main(["bootstrap", "--target", str(tmp_path), "--dry-run"]) == (
        BOOTSTRAP_STATUS
    )
    assert setup_cli.main(["install", "--target", str(tmp_path), "--dry-run", "--force"]) == (
        INSTALL_STATUS
    )
    assert calls == [
        ("bootstrap", {"target": tmp_path, "dry_run": True}),
        ("install", {"target": tmp_path, "dry_run": True, "force": True}),
    ]


@pytest.mark.parametrize("command", ("bootstrap", "install"))
@pytest.mark.parametrize("help_flag", ("-h", "--help"))
def test_setup_help_never_mutates(
    command: str,
    help_flag: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every help spelling exits before calling a mutating operation."""

    calls: list[str] = []

    def record_bootstrap(*, target: Path | None = None, dry_run: bool = False) -> None:
        calls.append("bootstrap")

    def record_install(
        *,
        target: Path | None = None,
        dry_run: bool = False,
        force: bool = False,
    ) -> None:
        calls.append("install")

    monkeypatch.setattr(setup_cli.setup, "bootstrap", record_bootstrap)
    monkeypatch.setattr(setup_cli.setup, "install", record_install)

    with pytest.raises(SystemExit) as raised:
        setup_cli.main([command, help_flag])

    assert raised.value.code == 0
    assert calls == []


@pytest.mark.parametrize("command", ("bootstrap", "install"))
def test_setup_unknown_options_never_mutate(
    command: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mistyped setup options fail parsing before behavior starts."""

    calls: list[str] = []

    def record_bootstrap(*, target: Path | None = None, dry_run: bool = False) -> None:
        calls.append("bootstrap")

    def record_install(
        *,
        target: Path | None = None,
        dry_run: bool = False,
        force: bool = False,
    ) -> None:
        calls.append("install")

    monkeypatch.setattr(setup_cli.setup, "bootstrap", record_bootstrap)
    monkeypatch.setattr(setup_cli.setup, "install", record_install)

    with pytest.raises(SystemExit) as raised:
        setup_cli.main([command, "--dry-rnu"])

    assert raised.value.code == ARGUMENT_ERROR_STATUS
    assert calls == []


def test_bootstrap_dry_run_does_not_create_virtualenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dependency preview does not create environments or install hooks."""

    monkeypatch.setattr(
        bootstrap,
        "ensure_virtualenv",
        lambda _root: pytest.fail("dry-run created a virtualenv"),
    )

    assert bootstrap.bootstrap(target=tmp_path, dry_run=True) == 0

    output = capsys.readouterr().out
    assert "would ensure virtualenv" in output
    assert "hooks are not installed by bootstrap" in output
    assert not (tmp_path / ".venv").exists()


def test_install_dry_run_skips_pre_commit_and_hook_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Integration preview avoids pre-commit execution and hook destinations."""

    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    monkeypatch.setattr(
        bootstrap,
        "install_pre_commit",
        lambda _root: pytest.fail("dry-run installed pre-commit"),
    )

    assert bootstrap.install(target=tmp_path, dry_run=True) == 0

    assert not (tmp_path / ".codex").exists()
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / ".agent-maintainer/backups").exists()


@pytest.mark.parametrize("command", ("bootstrap", "install"))
def test_top_level_setup_help_is_side_effect_free(command: str, tmp_path: Path) -> None:
    """The real package entrypoint prints subcommand help without writes."""

    completed = _run_setup(tmp_path, command, "--help")

    assert completed.returncode == 0
    assert "usage:" in completed.stdout.lower()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("command", ("bootstrap", "install"))
def test_top_level_setup_typo_is_side_effect_free(command: str, tmp_path: Path) -> None:
    """The real package entrypoint rejects unknown flags without writes."""

    completed = _run_setup(tmp_path, command, "--dry-rnu")

    assert completed.returncode == ARGUMENT_ERROR_STATUS
    assert "unrecognized arguments" in completed.stderr
    assert list(tmp_path.iterdir()) == []


def _run_setup(tmp_path: Path, command: str, option: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(REPO_ROOT / "src"),
        }
    )
    return subprocess.run(  # nosec B603
        [sys.executable, "-m", "agent_maintainer", command, option],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
