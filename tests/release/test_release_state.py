"""Release-only state drift checks."""

from __future__ import annotations

import os
import tomllib

import pytest

from tests.support.paths import REPO_ROOT

RUN_RELEASE_TESTS = os.environ.get("AGENT_MAINTAINER_RUN_RELEASE_TESTS") == "1"
release_only = pytest.mark.skipif(
    not RUN_RELEASE_TESTS,
    reason="set AGENT_MAINTAINER_RUN_RELEASE_TESTS=1 to run release checks",
)


def project_metadata() -> dict[str, object]:
    """Return parsed project metadata."""

    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject.get("project", {})
    assert isinstance(project, dict)
    return project


@pytest.mark.release
@release_only
def test_release_version_has_changelog_entry() -> None:
    """Release version must appear in the changelog."""

    version = str(project_metadata()["version"])
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert f"## {version}" in changelog


@pytest.mark.release
@release_only
def test_release_evidence_matches_version_when_present() -> None:
    """Existing release evidence must match the declared package version."""

    version = str(project_metadata()["version"])
    evidence_path = REPO_ROOT / "docs" / "releases" / f"{version}.md"

    if not evidence_path.exists():
        return

    evidence = evidence_path.read_text(encoding="utf-8")
    assert f"Agent Maintainer {version}" in evidence
    assert f"agent_maintainer-{version}" in evidence


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
