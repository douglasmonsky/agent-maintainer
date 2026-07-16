"""Tests preview-first Java/Gradle setup planning."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from agent_maintainer.core.setup_plans import (
    ReviewedFileEdit,
    SetupReviewError,
    apply_reviewed_edits,
    reviewed_edit_digest,
)
from agent_maintainer.ecosystems.java.semantic_edits import (
    SemanticEditResult,
    SemanticEditValidation,
    preview_semantic_edit_result,
    semantic_edit_result_digest,
)
from agent_maintainer.ecosystems.java.setup import (
    JavaSetupStatus,
    apply_java_setup,
    apply_semantic_edit_result,
    plan_java_setup,
    preview_java_setup,
)

FIXTURES = Path(__file__).parents[2] / "fixtures" / "java_gradle"

# docsync:evidence.start evidence.java.reviewed_setup_tests


@pytest.mark.parametrize(
    ("fixture", "build_path"),
    (
        ("groovy_single", "build.gradle"),
        ("kotlin_multi", "build.gradle.kts"),
    ),
)
def test_recognized_scaffolds_have_deterministic_reviewed_edits(
    tmp_path: Path,
    fixture: str,
    build_path: str,
) -> None:
    repo = _copy_fixture(tmp_path, fixture)

    plan = plan_java_setup(repo)
    preview = preview_java_setup(plan)

    assert plan.status == JavaSetupStatus.READY
    assert plan.semantic_edit is None
    assert build_path in preview
    assert "com.diffplug.spotless" in preview
    assert "config/checkstyle/checkstyle.xml" in {edit.path for edit in plan.edits}
    assert "config/pmd/pmd.xml" in {edit.path for edit in plan.edits}
    assert "gradle.properties" in {edit.path for edit in plan.edits}


def test_new_mixed_repository_uses_kotlin_default_without_touching_python(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'mixed'\n", encoding="utf-8")
    python_before = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")

    plan = plan_java_setup(tmp_path)
    apply_java_setup(plan, approved_digest=plan.review_digest)

    assert (tmp_path / "build.gradle.kts").exists()
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8") == python_before


def test_preview_and_apply_have_parity_and_second_plan_is_idempotent(tmp_path: Path) -> None:
    repo = _copy_fixture(tmp_path, "groovy_single")
    plan = plan_java_setup(repo)
    preview = preview_java_setup(plan)

    with pytest.raises(SetupReviewError, match="approved digest"):
        apply_java_setup(plan, approved_digest="wrong")
    apply_java_setup(plan, approved_digest=plan.review_digest)

    assert "+    id 'com.diffplug.spotless' version '8.8.0'" in preview
    assert "com.diffplug.spotless" in (repo / "build.gradle").read_text(encoding="utf-8")
    repeated = plan_java_setup(repo)
    assert repeated.status == JavaSetupStatus.UNCHANGED
    assert repeated.edits == ()


def test_existing_gradle_properties_are_preserved_when_coverage_floors_are_added(
    tmp_path: Path,
) -> None:
    repo = _copy_fixture(tmp_path, "groovy_single")
    properties = repo / "gradle.properties"
    properties.write_text("org.gradle.parallel=true\n", encoding="utf-8")

    plan = plan_java_setup(repo)
    edit = next(item for item in plan.edits if item.path == "gradle.properties")

    assert edit.before == "org.gradle.parallel=true\n"
    assert edit.after is not None
    assert edit.after.startswith("org.gradle.parallel=true\n")
    assert "agentMaintainer.jacoco.minimumLineCoverage=0.80" in edit.after
    assert "agentMaintainer.jacoco.minimumBranchCoverage=0.70" in edit.after


def test_arbitrary_build_returns_typed_semantic_edit_handoff(tmp_path: Path) -> None:
    build_file = tmp_path / "build.gradle.kts"
    build_file.write_text(
        "plugins { java }\nallprojects { repositories { mavenCentral() } }\n",
        encoding="utf-8",
    )

    plan = plan_java_setup(tmp_path)

    assert plan.status == JavaSetupStatus.SEMANTIC_EDIT
    assert {edit.path for edit in plan.edits} == {
        "config/checkstyle/checkstyle.xml",
        "config/pmd/pmd.xml",
        "gradle.properties",
    }
    assert plan.semantic_edit is not None
    assert plan.semantic_edit.path == "build.gradle.kts"
    assert "preserve existing build behavior" in plan.semantic_edit.forbidden_changes


def test_semantic_edit_result_requires_validation_and_reviewed_diff(tmp_path: Path) -> None:
    build_file = tmp_path / "build.gradle"
    original = "plugins { id 'java-library' }\nrepositories { mavenCentral() }\n"
    build_file.write_text(original, encoding="utf-8")
    plan = plan_java_setup(tmp_path)
    request = plan.semantic_edit
    assert request is not None
    updated = original + "// reviewed Agent Maintainer Java configuration\n"
    result = SemanticEditResult(
        path=request.path,
        original_text=original,
        updated_text=updated,
        validation=SemanticEditValidation(passed=True, details=("semantic review passed",)),
    )
    preview = preview_semantic_edit_result(request, result, additional_edits=plan.edits)
    digest = semantic_edit_result_digest(request, result, additional_edits=plan.edits)

    assert "validation: semantic review passed" in preview
    assert "+// reviewed Agent Maintainer Java configuration" in preview
    with pytest.raises(SetupReviewError, match="approved digest"):
        apply_semantic_edit_result(plan, result, approved_digest="wrong")
    apply_semantic_edit_result(plan, result, approved_digest=digest)
    assert build_file.read_text(encoding="utf-8") == updated
    assert (tmp_path / "config" / "checkstyle" / "checkstyle.xml").exists()


def test_semantic_edit_result_refuses_failed_validation(tmp_path: Path) -> None:
    build_file = tmp_path / "build.gradle"
    original = "plugins { id 'java-library' }\n"
    build_file.write_text(original, encoding="utf-8")
    plan = plan_java_setup(tmp_path)
    request = plan.semantic_edit
    assert request is not None
    result = SemanticEditResult(
        path=request.path,
        original_text=original,
        updated_text=f"{original}// proposed\n",
        validation=SemanticEditValidation(passed=False, details=("Gradle parse failed",)),
    )

    with pytest.raises(SetupReviewError, match="validation failed"):
        preview_semantic_edit_result(request, result)


def test_ambiguous_dsl_and_existing_ruleset_conflicts_refuse_safely(tmp_path: Path) -> None:
    (tmp_path / "build.gradle").write_text("", encoding="utf-8")
    (tmp_path / "build.gradle.kts").write_text("", encoding="utf-8")
    ambiguous = plan_java_setup(tmp_path)
    assert ambiguous.status == JavaSetupStatus.REFUSED
    assert "both Gradle DSL" in ambiguous.reason

    (tmp_path / "build.gradle.kts").unlink()
    (tmp_path / "build.gradle").write_text("plugins {\n    id 'java'\n}\n", encoding="utf-8")
    ruleset = tmp_path / "config" / "checkstyle" / "checkstyle.xml"
    ruleset.parent.mkdir(parents=True)
    ruleset.write_text("<custom/>\n", encoding="utf-8")
    conflict = plan_java_setup(tmp_path)
    assert conflict.status == JavaSetupStatus.REFUSED
    assert "existing managed ruleset differs" in conflict.reason


def test_reviewed_edits_refuse_stale_or_unconfined_sources(tmp_path: Path) -> None:
    build_file = tmp_path / "build.gradle"
    build_file.write_text("before\n", encoding="utf-8")
    stale = (ReviewedFileEdit("build.gradle", "before\n", "after\n", "test"),)
    digest = reviewed_edit_digest(stale)
    build_file.write_text("changed\n", encoding="utf-8")

    with pytest.raises(SetupReviewError, match="changed after review"):
        apply_reviewed_edits(tmp_path, stale, approved_digest=digest)

    escaping = (ReviewedFileEdit("../escape", None, "unsafe\n", "test"),)
    with pytest.raises(SetupReviewError, match="not repository-confined"):
        apply_reviewed_edits(
            tmp_path,
            escaping,
            approved_digest=reviewed_edit_digest(escaping),
        )


def _copy_fixture(tmp_path: Path, name: str) -> Path:
    return Path(shutil.copytree(FIXTURES / name, tmp_path / "repo"))


# docsync:evidence.end evidence.java.reviewed_setup_tests
