"""Tests PyPI Trusted Publishing workflow readiness."""

from __future__ import annotations

from pathlib import Path

PUBLISH_WORKFLOW = Path(".github/workflows/publish.yml")
RELEASE_CHECKLIST = Path("docs/release-checklist.md")
EVIDENCE_CONSUMER_JOB_COUNT = 3
EVIDENCE_BOUND_PUBLISH_JOB_COUNT = 3
EVIDENCE_SHA_USE_COUNT = 5
DISTRIBUTION_CONSUMER_JOB_COUNT = 3
DISTRIBUTION_PATH_COUNT = 4
DISTRIBUTION_VERIFY_COUNT = 4
INDEX_PUBLISH_JOB_COUNT = 2
RELEASE_PROFILES = ("full", "ci", "security", "manual", "release")


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
    assert "five clean-checkout matrix jobs" in normalized_text
    assert "Distribution construction runs independently in parallel" in normalized_text
    assert "publish workflow intentionally avoids dependency caches" in normalized_text


def test_publish_workflow_requires_exact_commit_release_evidence() -> None:
    """Publishing consumes all required profile evidence for the workflow SHA."""

    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    assert "release-profile-evidence:" in text
    assert "release-evidence:" in text
    assert "profile: [full, ci, security, manual, release]" in text
    for profile in RELEASE_PROFILES[:-1]:
        assert f"verify --profile {profile}" in text
        assert f'--manifest "$PROFILE_DIR/{profile}.json"' in text
    assert "release_evidence record" in text
    assert '--manifest "$PROFILE_DIR/release.json"' in text
    assert "release-profile-${{ github.sha }}-${{ matrix.profile }}" in text
    assert "pattern: release-profile-${{ github.sha }}-*" in text
    assert "merge-multiple: true" in text
    assert "release-evidence-${{ github.sha }}" in text
    assert "release_evidence aggregate" in text
    assert text.count("Validate exact-commit release evidence") == EVIDENCE_CONSUMER_JOB_COUNT
    assert text.count("EXPECTED_SHA: ${{ github.sha }}") >= EVIDENCE_SHA_USE_COUNT


def test_build_runs_in_parallel_with_release_evidence() -> None:
    """Non-publishing distribution construction does not serialize on profiles."""

    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")
    build_start = text.index("  build:")
    build_end = text.index("  # docsync:evidence.start", build_start)
    build_job = text[build_start:build_end]

    assert "\n    needs:" not in build_job
    assert "Download exact-commit release evidence" not in build_job
    assert "Validate exact-commit release evidence" not in build_job


def test_terminal_publish_jobs_depend_on_evidence_and_build() -> None:
    """Every externally mutating job validates both upstream artifacts."""

    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

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


def test_publish_workflow_verifies_exact_distribution_bytes() -> None:
    """Every transfer and terminal release action consumes the verified bundle."""

    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")
    bundle = "$RUNNER_TEMP/python-distributions"

    assert "release_artifacts create" in text
    assert f'--bundle "{bundle}"' in text
    assert text.count("release_artifacts verify") == DISTRIBUTION_VERIFY_COUNT
    assert text.count("--expected-manifest-sha256") == DISTRIBUTION_VERIFY_COUNT
    assert (
        "distribution_manifest_sha256: ${{ steps.distribution_bundle.outputs.manifest_sha256 }}"
    ) in text
    assert (
        text.count(
            "EXPECTED_MANIFEST_SHA256: ${{ needs.build.outputs.distribution_manifest_sha256 }}"
        )
        == DISTRIBUTION_CONSUMER_JOB_COUNT
    )
    assert text.count("Download verified distribution bundle") == DISTRIBUTION_CONSUMER_JOB_COUNT
    assert "path: ${{ runner.temp }}/python-distributions/" in text
    assert text.count("path: ${{ runner.temp }}/python-distributions") >= DISTRIBUTION_PATH_COUNT
    assert (
        text.count("packages-dir: ${{ runner.temp }}/python-distributions/packages/")
        == INDEX_PUBLISH_JOB_COUNT
    )
    assert '"$RUNNER_TEMP/python-distributions/packages/"*' in text
    assert "packages-dir: dist/" not in text

    for job_name in (
        "attach-github-release-artifacts",
        "publish-testpypi",
        "publish-pypi",
    ):
        job_start = text.index(f"  {job_name}:")
        download = text.index("Download verified distribution bundle", job_start)
        verification = text.index("Verify distribution bundle", download)
        terminal_action = (
            text.index("Attach distributions to GitHub release", job_start)
            if job_name == "attach-github-release-artifacts"
            else text.index("Publish to ", job_start)
        )
        assert download < verification < terminal_action
