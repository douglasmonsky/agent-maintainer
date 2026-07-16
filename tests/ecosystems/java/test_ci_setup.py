"""Tests reviewed Java/Gradle CI workflow planning."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.ecosystems.java.setup import (
    JavaCiConvention,
    JavaSetupStatus,
    apply_java_setup,
    plan_java_ci_setup,
    preview_java_setup,
)

STATIC_TASKS = ("spotlessCheck", "spotbugsMain", "checkstyleMain", "pmdMain")
TEST_TASKS = ("test", "jacocoTestReport", "jacocoTestCoverageVerification")
TEXT_ENCODING = "utf-8"
WORKFLOW_PATH = ".github/workflows/agent-maintainer-java.yml"

# docsync:evidence.start evidence.java.ci_setup_tests


def test_ci_plan_adds_parallel_cached_jobs(tmp_path: Path) -> None:
    """Known GitHub/JDK conventions produce two independent cached jobs."""
    plan = plan_java_ci_setup(
        tmp_path,
        ci_convention(spotless_ratchet_ref="origin/main"),
    )
    preview = preview_java_setup(plan)

    assert plan.status == JavaSetupStatus.READY
    expected_fragments = (
        "static-and-policy:",
        "tests-and-coverage:",
        "cache: gradle",
        "fetch-depth: 0",
        "origin/main",
    )
    assert all(fragment in preview for fragment in expected_fragments)


def test_ci_plan_preserves_existing_workflow(tmp_path: Path) -> None:
    """Applying the dedicated workflow never rewrites repository-owned CI."""
    existing = tmp_path / ".github" / "workflows" / "build.yml"
    existing.parent.mkdir(parents=True)
    existing.write_text("name: existing\n", encoding=TEXT_ENCODING)
    plan = plan_java_ci_setup(
        tmp_path,
        ci_convention(jdk_distribution="zulu", jdk_version="17"),
    )

    changed = apply_java_setup(plan, approved_digest=plan.review_digest)

    assert changed == (tmp_path / WORKFLOW_PATH,)
    assert existing.read_text(encoding=TEXT_ENCODING) == "name: existing\n"
    assert "distribution: zulu" in changed[0].read_text(encoding=TEXT_ENCODING)


def test_ci_plan_refuses_unknown_framework(tmp_path: Path) -> None:
    """Unknown CI structures require a separate reviewed semantic plan."""
    plan = plan_java_ci_setup(
        tmp_path,
        ci_convention(framework="gitlab"),
    )

    assert plan.status == JavaSetupStatus.REFUSED
    assert "unsupported CI framework" in plan.reason


def test_ci_plan_refuses_existing_managed_path(tmp_path: Path) -> None:
    """A differing dedicated workflow is never overwritten automatically."""
    workflow = tmp_path / WORKFLOW_PATH
    workflow.parent.mkdir(parents=True)
    workflow.write_text("name: custom\n", encoding=TEXT_ENCODING)

    plan = plan_java_ci_setup(
        tmp_path,
        ci_convention(),
    )

    assert plan.status == JavaSetupStatus.REFUSED
    assert "will not be overwritten" in plan.reason


def ci_convention(
    *,
    framework: str = "github-actions",
    jdk_distribution: str = "temurin",
    jdk_version: str = "21",
    spotless_ratchet_ref: str = "",
) -> JavaCiConvention:
    """Return one explicit repository CI convention."""
    return JavaCiConvention(
        framework,
        jdk_distribution,
        jdk_version,
        STATIC_TASKS,
        TEST_TASKS,
        spotless_ratchet_ref,
    )


# docsync:evidence.end evidence.java.ci_setup_tests
