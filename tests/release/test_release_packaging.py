"""Release-only packaging checks for Agent Maintainer."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import sys
import tarfile
import tomllib
import venv
import zipfile
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer import release_artifacts_io
from tests.support.paths import REPO_ROOT

RUN_RELEASE_TESTS = os.environ.get("AGENT_MAINTAINER_RUN_RELEASE_TESTS") == "1"
release_only = pytest.mark.skipif(
    not RUN_RELEASE_TESTS,
    reason="set AGENT_MAINTAINER_RUN_RELEASE_TESTS=1 to run release packaging checks",
)

EXTRAS = ("core", "agent", "hardening", "manual", "mcp", "all")
SOURCE_METADATA = REPO_ROOT / "src" / "agent_maintainer.egg-info"
BUILD_DIR = REPO_ROOT / "build"
GIT_SHA_LENGTH = 40
SYNTHETIC_RELEASE_SHA = "a" * GIT_SHA_LENGTH
SCRIPT_HELP_MARKERS = {
    "agent-maintainer": "python -m agent_maintainer verify --profile precommit",
    "archguard": "tach-config",
    "docsync": "Documentation traceability",
}


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


def smoke_setup_skill(python: Path) -> None:
    """Assert an installed artifact exposes skill data and its public command."""
    resource_check = (
        "from importlib import resources; "
        "root = resources.files('agent_maintainer.skill') / 'resources' / "
        "'agent-maintainer-setup'; "
        "assert (root / 'SKILL.md').is_file(); "
        "assert (root / 'agents' / 'openai.yaml').is_file()"
    )
    result = run([str(python), "-c", resource_check])
    assert result.returncode == 0, result.stdout + result.stderr

    executable = python.parent / "agent-maintainer"
    result = run([str(executable), "skill", "--help"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "install" in result.stdout
    assert "status" in result.stdout
    assert "uninstall" in result.stdout


def advertised_console_scripts() -> tuple[str, ...]:
    """Return the console scripts advertised by package metadata."""

    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        metadata = _object_mapping(tomllib.load(handle))
    project = _object_mapping(metadata.get("project"))
    scripts = _object_mapping(project.get("scripts"))
    return tuple(sorted(scripts))


def _object_mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def smoke_console_scripts(python: Path) -> None:
    """Run help for every advertised script from one artifact environment."""

    expected_scripts = tuple(sorted(SCRIPT_HELP_MARKERS))
    assert advertised_console_scripts() == expected_scripts
    for script in expected_scripts:
        result = run([str(python.parent / script), "--help"])
        assert result.returncode == 0, result.stdout + result.stderr
        assert SCRIPT_HELP_MARKERS[script] in result.stdout


# docsync:evidence.start evidence.release.packaging_tests
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
@pytest.mark.artifact_smoke
@pytest.mark.owner_contract
@release_only
def test_release_builds_artifacts_and_installs_console_scripts(
    tmp_path: Path,
) -> None:
    """Built wheel and sdist install cleanly and expose every console script."""
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

    built_wheel = next(dist_dir.glob("agent_maintainer-*.whl"))
    built_sdist = next(dist_dir.glob("agent_maintainer-*.tar.gz"))
    built_artifacts = (built_wheel, built_sdist)

    result = run(
        [
            sys.executable,
            "-m",
            "twine",
            "check",
            *(str(artifact) for artifact in built_artifacts),
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr

    bundle_dir = tmp_path / "python-distributions"
    created = release_artifacts_io.create_distribution_bundle(
        dist_dir,
        bundle_dir,
        expected_sha=SYNTHETIC_RELEASE_SHA,
    )
    verified = release_artifacts_io.verify_distribution_bundle(
        bundle_dir,
        expected_sha=SYNTHETIC_RELEASE_SHA,
        expected_manifest_sha256=created.manifest_sha256,
    )
    artifacts = tuple(bundle_dir / artifact.path for artifact in verified.artifacts)

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
        smoke_console_scripts(python)
        smoke_setup_skill(python)


# docsync:evidence.end evidence.release.packaging_tests
