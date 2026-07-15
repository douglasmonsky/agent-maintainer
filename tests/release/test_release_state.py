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
def test_release_version_has_candidate_changelog_entry() -> None:
    """Candidate version must appear as the explicit Unreleased target."""

    version = str(project_metadata()["version"])
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert f"## Unreleased (target: {version})" in changelog
    assert f"`{version}` is an unpublished release candidate" in changelog


@pytest.mark.release
@release_only
def test_release_candidate_notes_are_truthful() -> None:
    """Candidate notes identify the version without inventing release evidence."""

    version = str(project_metadata()["version"])
    candidate_path = REPO_ROOT / "docs" / "releases" / f"{version}.md"
    candidate = candidate_path.read_text(encoding="utf-8")

    assert f"# Agent Maintainer {version} Candidate Notes" in candidate
    assert "- Status: `unpublished`" in candidate
    for false_evidence in (
        "Git tag:",
        "GitHub release:",
        "TestPyPI workflow:",
        "PyPI workflow:",
        "sha256:",
        f"agent_maintainer-{version}",
    ):
        assert false_evidence not in candidate


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
