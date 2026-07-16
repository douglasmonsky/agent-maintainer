"""Tests safe Spotless native ratchet setup and verification."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from agent_maintainer.config.java import JavaGradleConfig
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.ecosystems.java import runner
from agent_maintainer.ecosystems.java.provider import JavaProviderConfigurationError
from agent_maintainer.ecosystems.java.setup import (
    JavaSetupStatus,
    plan_java_setup,
    preview_java_setup,
)
from agent_maintainer.models import PRECOMMIT_PROFILE

FIXTURE_ROOT = Path(__file__).parents[2] / "fixtures" / "java_gradle" / "established_ratchet"
RATCHET_REF = "origin/main"
TEXT_ENCODING = "utf-8"


def test_setup_renders_explicit_ratchet_ref(tmp_path: Path) -> None:
    """An available explicit base ref becomes deterministic Spotless config."""
    repo = copy_fixture(tmp_path)
    initialize_git(repo)

    plan = plan_java_setup(repo, spotless_ratchet_ref=RATCHET_REF)

    assert plan.status == JavaSetupStatus.READY
    assert 'ratchetFrom("origin/main")' in preview_java_setup(plan)


def test_setup_refuses_unavailable_ref(tmp_path: Path) -> None:
    """A missing ref is a setup failure with CI fetch guidance."""
    repo = copy_fixture(tmp_path)
    initialize_git(repo)

    plan = plan_java_setup(repo, spotless_ratchet_ref="origin/missing")

    assert plan.status == JavaSetupStatus.REFUSED
    assert "unavailable" in plan.reason
    assert "CI must fetch" in plan.reason


@pytest.mark.parametrize("ratchet_ref", ("-main", "origin/../main", "origin/main\napply"))
def test_setup_refuses_unsafe_ref(tmp_path: Path, ratchet_ref: str) -> None:
    """Unsafe base refs never reach Git or Gradle rendering."""
    repo = copy_fixture(tmp_path)
    initialize_git(repo)

    plan = plan_java_setup(repo, spotless_ratchet_ref=ratchet_ref)

    assert plan.status == JavaSetupStatus.REFUSED
    assert "unsupported characters" in plan.reason


def test_setup_explains_shallow_checkout(tmp_path: Path) -> None:
    """A shallow checkout explains why a missing base ref cannot be used."""
    repo = copy_fixture(tmp_path)
    head = initialize_git(repo)
    (repo / ".git" / "shallow").write_text(f"{head}\n", encoding=TEXT_ENCODING)

    plan = plan_java_setup(repo, spotless_ratchet_ref="origin/missing")

    assert plan.status == JavaSetupStatus.REFUSED
    assert "shallow" in plan.reason
    assert "fetch-depth" in plan.reason


def test_runner_refuses_unavailable_ref(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verification fails configuration before Gradle when its ref is absent."""
    repo = copy_fixture(tmp_path)
    initialize_git(repo)
    run_wrapper = configure_runner(monkeypatch, repo, "origin/missing", "spotlessCheck")

    with pytest.raises(JavaProviderConfigurationError, match="CI must fetch"):
        runner._run_group(repo, "format", PRECOMMIT_PROFILE)

    run_wrapper.assert_not_called()


def test_runner_never_applies_formatting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutating Spotless tasks are configuration failures during verification."""
    repo = copy_fixture(tmp_path)
    initialize_git(repo)
    run_wrapper = configure_runner(monkeypatch, repo, RATCHET_REF, ":app:spotlessApply")

    with pytest.raises(JavaProviderConfigurationError, match="mutating Spotless task"):
        runner._run_group(repo, "format", PRECOMMIT_PROFILE)

    run_wrapper.assert_not_called()


def test_runner_executes_check_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An available ref permits only the configured check task."""
    repo = copy_fixture(tmp_path)
    initialize_git(repo)
    run_wrapper = configure_runner(monkeypatch, repo, RATCHET_REF, "spotlessCheck")

    outcome = runner._run_group(repo, "format", PRECOMMIT_PROFILE)

    assert outcome.exit_code == 0
    assert run_wrapper.call_args.args[-1] == ("spotlessCheck",)


def copy_fixture(target: Path) -> Path:
    """Copy the established-repository fixture into a writable test root."""
    shutil.copytree(FIXTURE_ROOT, target, dirs_exist_ok=True)
    return target


def initialize_git(repo: Path) -> str:
    """Create a commit and its remote-default reference."""
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "tests@example.invalid")
    git(repo, "config", "user.name", "Agent Maintainer Tests")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "fixture")
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/origin/main", head)
    return head


def git(repo: Path, *args: str) -> str:
    """Run one fixed git test-fixture command."""
    completed = subprocess.run(  # nosec B603
        ("git", *args),
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def configure_runner(
    monkeypatch: pytest.MonkeyPatch,
    repo: Path,
    ratchet_ref: str,
    task: str,
) -> Mock:
    """Install deterministic configuration and wrapper doubles."""
    config = MaintainerConfig(
        java=JavaGradleConfig(
            enabled=True,
            checks=("spotless",),
            spotless_tasks=(task,),
            spotless_ratchet_ref=ratchet_ref,
        )
    )
    resolved = runner.wrapper.ResolvedGradleWrapper(repo, repo, repo / "gradlew")
    run_wrapper = Mock(return_value=0)
    monkeypatch.setattr(runner, "_load_java_config", lambda _workspace: config)
    monkeypatch.setattr(runner.wrapper, "resolve_gradle_wrapper", lambda *_args: resolved)
    monkeypatch.setattr(runner, "_run_wrapper", run_wrapper)
    return run_wrapper
