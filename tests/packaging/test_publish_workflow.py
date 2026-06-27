"""Tests PyPI Trusted Publishing workflow readiness."""

from __future__ import annotations

from pathlib import Path

PUBLISH_WORKFLOW = Path(".github/workflows/publish.yml")
RELEASE_CHECKLIST = Path("docs/release-checklist.md")


def test_publish_workflow_uses_trusted_publishing() -> None:
    """The publishing workflow uses OIDC instead of stored PyPI credentials."""

    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "release:" in text
    assert "pull_request:" not in text
    assert "\n  push:" not in text
    assert "id-token: write" in text
    assert "pypa/gh-action-pypi-publish@cef221092ed1bacb1cc03d23a2d87d1d172e277b" in text
    assert "repository-url: https://test.pypi.org/legacy/" in text
    assert "name: testpypi" in text
    assert "name: pypi" in text

    forbidden = ("password", "username", "PYPI_TOKEN", "TWINE_PASSWORD", ".pypirc")
    offenders = [fragment for fragment in forbidden if fragment in text]

    assert offenders == []


def test_release_checklist_documents_trusted_publisher_values() -> None:
    """The release checklist tells maintainers which PyPI values to enter."""

    text = RELEASE_CHECKLIST.read_text(encoding="utf-8")

    assert "project name `agent-maintainer`" in text
    assert "owner `douglasmonsky`" in text
    assert "repository `agent-maintainer`" in text
    assert "workflow `publish.yml`" in text
    assert "environment `pypi`" in text
    assert "environment `testpypi`" in text
