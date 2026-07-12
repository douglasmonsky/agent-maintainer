"""Release-only state drift checks."""

from __future__ import annotations

import os
import tomllib

import pytest

from agent_maintainer.core.structured_values import json_object
from tests.support.paths import REPO_ROOT

RUN_RELEASE_TESTS = os.environ.get("AGENT_MAINTAINER_RUN_RELEASE_TESTS") == "1"
release_only = pytest.mark.skipif(
    not RUN_RELEASE_TESTS,
    reason="set AGENT_MAINTAINER_RUN_RELEASE_TESTS=1 to run release checks",
)


def project_metadata() -> dict[str, object]:
    """Return parsed project metadata."""

    pyproject: dict[str, object] = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"),
    )
    project = json_object(pyproject.get("project"))
    assert project is not None
    return project


@pytest.mark.release
@release_only
def test_release_version_has_dated_changelog_entry() -> None:
    """Published version must appear in a dated release section."""

    version = str(project_metadata()["version"])
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert f"## {version} - 2026-07-12" in changelog
    assert f"{version} is an unpublished release candidate" not in changelog


@pytest.mark.release
@release_only
def test_release_notes_record_published_b6_evidence() -> None:
    """Published b6 notes retain exact immutable release evidence."""

    version = str(project_metadata()["version"])
    candidate_path = REPO_ROOT / "docs" / "releases" / f"{version}.md"
    candidate = candidate_path.read_text(encoding="utf-8")

    assert f"# Agent Maintainer {version} Release Evidence" in candidate
    for evidence in (
        "3492f6fd8459c9de24a714a84b65d53766a0d606",
        "v0.1.0b6",
        "29208426926",
        "29208792067",
        "29209369320",
        "f81ea2c7b1c7ffd493f94ca528c954fa1aa664ed39b4e9b496d6966c2cd4bd15",
        "9241b39c85be42c44567b396df9d503f1044e63d417f738fcb7047b83a88afe4",
        "39e6e12845a02e690904a7902d4ade6330193cde945b42ebb827935865717945",
        "3d27c3c77c2d07c8491c25e0d42e9f185be1e6672f10e5bfc93fa802b352078f",
        "Real-turn smoke: `passed`",
        "TestPyPI index smoke: `passed`",
        "PyPI index smoke: `passed`",
    ):
        assert evidence in candidate


@pytest.mark.release
@release_only
def test_publish_workflow_uses_expected_trusted_publisher_environments() -> None:
    """Publish workflow environment names must match PyPI Trusted Publisher setup."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "publish.yml").read_text(
        encoding="utf-8",
    )

    assert "name: testpypi" in workflow
    assert "name: pypi" in workflow
    assert "id-token: write" in workflow


@pytest.mark.release
@release_only
def test_public_metadata_urls_match_repository() -> None:
    """Release metadata must point at the public repository."""

    urls = project_metadata()["urls"]
    assert isinstance(urls, dict)
    assert urls["Repository"] == "https://github.com/douglasmonsky/agent-maintainer"
    assert urls["Issues"] == "https://github.com/douglasmonsky/agent-maintainer/issues"
    assert urls["Documentation"] == "https://github.com/douglasmonsky/agent-maintainer#readme"
