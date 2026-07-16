"""Tests hermetic grouped Java/Gradle runner execution."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from agent_maintainer.ecosystems.java import artifacts as java_artifacts
from agent_maintainer.ecosystems.java import runner

FIXTURES = Path(__file__).parents[1] / "fixtures" / "java_gradle"
GRADLE_FAILURE_EXIT_CODE = 7
LARGE_TASK_COUNT = 300


def test_main_runs_wrapper_with_exact_args_and_gradle_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _copy_fixture(tmp_path, "groovy-single-project")
    gradle_root = repo / "backend"
    gradle_root.mkdir()
    for name in ("gradlew", "settings.gradle", "build.gradle"):
        shutil.move(repo / name, gradle_root / name)
    _write_config(
        repo,
        gradle_root="backend",
        checks=("spotbugs", "checkstyle"),
        task_fields={
            "spotbugs_tasks": ("spotbugsMain", "sharedTask"),
            "checkstyle_tasks": ("sharedTask", "checkstyleMain"),
        },
    )
    records, artifacts = _runner_environment(tmp_path, monkeypatch)
    monkeypatch.chdir(repo)

    exit_code = runner.main(["--group", "static"])

    assert exit_code == 0
    assert (records / "cwd.txt").read_text(encoding="utf-8").strip() == str(gradle_root)
    assert (records / "argv.txt").read_text(encoding="utf-8").splitlines() == [
        "--console=plain",
        "--continue",
        "spotbugsMain",
        "sharedTask",
        "checkstyleMain",
    ]
    artifact = _read_artifact(artifacts, "static")
    assert artifact["status"] == "passed"
    assert artifact["tasks"] == ["spotbugsMain", "sharedTask", "checkstyleMain"]
    assert artifact["reports_parsed"] is False
    assert artifact["evidence_status"] == "execution-only"


def test_main_propagates_gradle_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _copy_fixture(tmp_path, "groovy-single-project")
    _write_config(repo, checks=("test",), task_fields={"test_tasks": ("test",)})
    _, artifacts = _runner_environment(tmp_path, monkeypatch)
    monkeypatch.setenv("JAVA_RUNNER_TEST_EXIT_CODE", str(GRADLE_FAILURE_EXIT_CODE))
    monkeypatch.chdir(repo)

    assert runner.main(["--group", "tests"]) == GRADLE_FAILURE_EXIT_CODE
    assert _read_artifact(artifacts, "tests")["status"] == "gradle-failed"


def test_main_fails_selected_tool_without_tasks_before_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _copy_fixture(tmp_path, "groovy-single-project")
    _write_config(repo, checks=("spotbugs",), task_fields={})
    records, artifacts = _runner_environment(tmp_path, monkeypatch)
    monkeypatch.chdir(repo)

    assert runner.main(["--group", "static"]) == java_artifacts.CONFIGURATION_EXIT_CODE
    assert not (records / "argv.txt").exists()
    artifact = _read_artifact(artifacts, "static")
    assert artifact["status"] == "configuration-error"
    error = artifact["error"]
    assert isinstance(error, str)
    assert "java.spotbugs_tasks" in error


def test_main_sanitizes_missing_wrapper_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _copy_fixture(tmp_path, "missing-wrapper")
    _write_config(repo, checks=("test",), task_fields={"test_tasks": ("test",)})
    _, artifacts = _runner_environment(tmp_path, monkeypatch)
    monkeypatch.chdir(repo)

    assert runner.main(["--group", "tests"]) == java_artifacts.CONFIGURATION_EXIT_CODE
    artifact_path = _artifact_path(artifacts, "tests")
    artifact_text = artifact_path.read_text(encoding="utf-8")
    assert str(repo) not in artifact_text
    assert json.loads(artifact_text)["status"] == "configuration-error"


def test_main_invokes_subprocess_without_shell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _copy_fixture(tmp_path, "groovy-single-project")
    _write_config(repo, checks=("test",), task_fields={"test_tasks": ("test",)})
    _runner_environment(tmp_path, monkeypatch)
    observed: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.update(command=command, **kwargs)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.chdir(repo)

    assert runner.main(["--group", "tests"]) == 0
    assert observed["shell"] is False
    assert observed["check"] is False
    assert observed["cwd"] == repo.resolve()


def test_artifact_is_bounded_when_task_list_is_large(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _copy_fixture(tmp_path, "groovy-single-project")
    tasks = tuple(f"task{index}" for index in range(LARGE_TASK_COUNT))
    _write_config(repo, checks=("test",), task_fields={"test_tasks": tasks})
    _, artifacts = _runner_environment(tmp_path, monkeypatch)
    monkeypatch.chdir(repo)

    assert runner.main(["--group", "tests"]) == 0
    artifact_path = _artifact_path(artifacts, "tests")
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact_path.stat().st_size <= java_artifacts.MAX_ARTIFACT_BYTES
    assert artifact["task_count"] == LARGE_TASK_COUNT
    assert artifact["tasks_truncated"] is True


def _copy_fixture(tmp_path: Path, name: str) -> Path:
    return Path(shutil.copytree(FIXTURES / name, tmp_path / "repo"))


def _write_config(
    repo: Path,
    *,
    checks: tuple[str, ...],
    task_fields: dict[str, tuple[str, ...]],
    gradle_root: str = ".",
) -> None:
    lines = [
        "[tool.agent_maintainer.java]",
        "enabled = true",
        f"gradle_root = {json.dumps(gradle_root)}",
        f"checks = {json.dumps(checks)}",
    ]
    lines.extend(f"{field} = {json.dumps(tasks)}" for field, tasks in task_fields.items())
    (repo / "pyproject.toml").write_text("\n".join(lines), encoding="utf-8")


def _runner_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path]:
    records = tmp_path / "records"
    artifacts = tmp_path / "artifacts"
    records.mkdir()
    monkeypatch.setenv("JAVA_RUNNER_TEST_RECORD_DIR", str(records))
    monkeypatch.setenv("_AGENT_MAINTAINER_VERIFY_PROFILE", "full")
    monkeypatch.setenv("AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR", str(artifacts))
    return records, artifacts


def _artifact_path(artifacts: Path, group: str) -> Path:
    return artifacts / "java-gradle" / f"java-gradle-{group}.json"


def _read_artifact(artifacts: Path, group: str) -> dict[str, object]:
    return json.loads(_artifact_path(artifacts, group).read_text(encoding="utf-8"))
