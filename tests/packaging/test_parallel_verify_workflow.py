"""Contract tests for fail-closed parallel pull-request verification."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "verify.yml"
PARTIAL_GROUP_COUNT = 2


def workflow_text() -> str:
    """Return the verified workflow source."""

    return WORKFLOW.read_text(encoding="utf-8")


def job_body(text: str, job: str, next_job: str | None) -> str:
    """Return one top-level workflow job body."""

    start = text.index(f"  {job}:")
    if next_job is None:
        return text[start:]
    return text[start : text.index(f"  {next_job}:", start)]


def test_verify_workflow_runs_verifier_owned_groups_in_parallel() -> None:
    """Independent jobs select groups through the product CLI contract."""

    text = workflow_text()
    tests_job = job_body(text, "tests-and-coverage", "static-and-policy")
    static_job = job_body(text, "static-and-policy", "verify")

    assert "--group tests-and-coverage" in tests_job
    assert "--group static-and-policy" in static_job
    assert "Set up Node" not in tests_job
    assert "Install external Agent Maintainer tools" not in tests_job
    assert "Set up Node" in static_job
    assert "Install external Agent Maintainer tools" in static_job
    assert "name: verify-tests-and-coverage-${{ github.sha }}" in tests_job
    assert "name: verify-static-and-policy-${{ github.sha }}" in static_job


def test_verify_aggregate_job_preserves_protected_job_name_and_fails_closed() -> None:
    """The stable verify job aggregates both exact-run manifests."""

    text = workflow_text()
    aggregate_job = job_body(text, "verify", None)

    assert "needs: [tests-and-coverage, static-and-policy]" in aggregate_job
    assert "if: always()" in aggregate_job
    assert aggregate_job.count("actions/download-artifact@") == PARTIAL_GROUP_COUNT
    assert "name: verify-tests-and-coverage-${{ github.sha }}" in aggregate_job
    assert "name: verify-static-and-policy-${{ github.sha }}" in aggregate_job
    assert "--aggregate-partial partials/tests-and-coverage/manifest.json" in aggregate_job
    assert "--aggregate-partial partials/static-and-policy/manifest.json" in aggregate_job
    assert "--aggregate-output .verify-logs/manifest.json" in aggregate_job
    assert "name: verify-logs" in aggregate_job


def test_python_compatibility_matrix_remains_independent() -> None:
    """Parallel quality checks do not weaken supported-version coverage."""

    text = workflow_text()
    compatibility = job_body(text, "python-compatibility", "tests-and-coverage")

    assert 'python-version: ["3.11", "3.12", "3.13", "3.14"]' in compatibility
    assert "needs:" not in compatibility
