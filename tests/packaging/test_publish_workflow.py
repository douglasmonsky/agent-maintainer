"""Tests PyPI Trusted Publishing workflow readiness."""

from __future__ import annotations

from pathlib import Path

PUBLISH_WORKFLOW = Path(".github/workflows/publish.yml")
RELEASE_CHECKLIST = Path("docs/release-checklist.md")
EVIDENCE_CONSUMER_JOB_COUNT = 4
EVIDENCE_BOUND_PUBLISH_JOB_COUNT = 3
EVIDENCE_SHA_USE_COUNT = 5


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
    normalized_text = " ".join(text.split())

    assert "project name `agent-maintainer`" in normalized_text
    assert "owner `douglasmonsky`" in normalized_text
    assert "repository `agent-maintainer`" in normalized_text
    assert "workflow `publish.yml`" in normalized_text
    assert "environment `pypi`" in normalized_text
    assert "environment `testpypi`" in normalized_text


def test_publish_workflow_requires_exact_commit_release_evidence() -> None:
    """Publishing consumes all required profile evidence for the workflow SHA."""

    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    assert "release-evidence:" in text
    for profile in ("full", "ci", "security", "manual"):
        assert f"verify --profile {profile}" in text
        assert f'--manifest "$PROFILE_DIR/{profile}.json"' in text
    assert "release_evidence record" in text
    assert '--manifest "$PROFILE_DIR/release.json"' in text
    assert "release-evidence-${{ github.sha }}" in text
    assert "release_evidence aggregate" in text
    assert text.count("Validate exact-commit release evidence") == EVIDENCE_CONSUMER_JOB_COUNT
    assert text.count("EXPECTED_SHA: ${{ github.sha }}") >= EVIDENCE_SHA_USE_COUNT


def test_publish_jobs_depend_on_release_evidence() -> None:
    """No build, attachment, or index publish job bypasses the evidence job."""

    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    assert "build:\n    name: build distributions\n    needs: release-evidence" in text
    assert text.count("needs: [release-evidence, build]") == EVIDENCE_BOUND_PUBLISH_JOB_COUNT
    for job_name in (
        "attach-github-release-artifacts",
        "publish-testpypi",
        "publish-pypi",
    ):
        job_start = text.index(f"  {job_name}:")
        validation = text.index("Validate exact-commit release evidence", job_start)
        terminal_action = (
            text.index("Attach distributions to GitHub release", job_start)
            if job_name == "attach-github-release-artifacts"
            else text.index("Publish to ", job_start)
        )
        assert validation < terminal_action
