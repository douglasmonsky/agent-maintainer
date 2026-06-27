"""Release-only packaging checks for Agent Maintainer."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest

from tests.support.paths import REPO_ROOT

RUN_RELEASE_TESTS = os.environ.get("AGENT_MAINTAINER_RUN_RELEASE_TESTS") == "1"
release_only = pytest.mark.skipif(
    not RUN_RELEASE_TESTS,
    reason="set AGENT_MAINTAINER_RUN_RELEASE_TESTS=1 to run release packaging checks",
)

EXTRAS = ("core", "agent", "hardening", "manual", "all")
SOURCE_METADATA = REPO_ROOT / "src" / "agent_maintainer.egg-info"
BUILD_DIR = REPO_ROOT / "build"


def run(command: list[str], *, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    """Run a release command and keep output for assertion failures."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(  # nosec B603
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def venv_python(path: Path) -> Path:
    """Create a virtual environment and return its Python executable."""
    venv.EnvBuilder(with_pip=True).create(path)
    return path / "bin" / "python"


def cleanup_source_metadata() -> None:
    """Remove generated metadata left by package build commands."""
    shutil.rmtree(SOURCE_METADATA, ignore_errors=True)
    shutil.rmtree(BUILD_DIR, ignore_errors=True)


def artifact_contains_license(path: Path) -> bool:
    """Return whether a built package artifact includes the MIT license file."""
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return any(name.endswith(".dist-info/licenses/LICENSE") for name in archive.namelist())

    with tarfile.open(path) as archive:
        return any(name.endswith("/LICENSE") for name in archive.getnames())


@pytest.mark.release
@release_only
@pytest.mark.parametrize("extra", EXTRAS)
def test_release_extra_dependency_graph_installs(tmp_path: Path, extra: str) -> None:
    """Release extras resolve and install with dependencies in a clean venv."""
    python = venv_python(tmp_path / f"venv-{extra}")

    result = run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            f"{REPO_ROOT}[{extra}]",
        ]
    )

    assert result.returncode == 0, result.stdout + result.stderr

    result = run([str(python), "-c", "import agent_maintainer; import archguard"])
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.release
@release_only
def test_release_builds_artifacts_and_installs_console_script(
    tmp_path: Path,
) -> None:
    """Built wheel and sdist install cleanly and expose console script."""
    dist_dir = tmp_path / "dist"
    try:
        result = run(
            [
                sys.executable,
                "-m",
                "build",
                "--sdist",
                "--wheel",
                "--outdir",
                str(dist_dir),
            ]
        )
    finally:
        cleanup_source_metadata()
    assert result.returncode == 0, result.stdout + result.stderr

    wheel = next(dist_dir.glob("agent_maintainer-*.whl"))
    sdist = next(dist_dir.glob("agent_maintainer-*.tar.gz"))
    artifacts = (wheel, sdist)

    result = run(
        [
            sys.executable,
            "-m",
            "twine",
            "check",
            *(str(artifact) for artifact in artifacts),
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr

    for index, artifact in enumerate(artifacts, start=1):
        assert artifact_contains_license(artifact)
        python = venv_python(tmp_path / f"artifact-install-{index}")
        result = run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                f"agent-maintainer[core] @ {artifact.as_uri()}",
            ]
        )
        assert result.returncode == 0, result.stdout + result.stderr

        result = run([str(python), "-m", "pip", "show", "agent-maintainer"])
        assert result.returncode == 0, result.stdout + result.stderr

        result = run(
            [
                str(python.parent / "agent-maintainer"),
                "--help",
            ]
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "python -m agent_maintainer verify --profile precommit" in result.stdout
        result = run(
            [
                str(python.parent / "archguard"),
                "--help",
            ]
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "tach-config" in result.stdout
