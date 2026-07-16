"""Preview-first Java/Gradle setup planning and semantic-edit handoffs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from agent_maintainer.core.setup_plans import (
    ReviewedFileEdit,
    SetupReviewError,
    apply_reviewed_edits,
    render_reviewed_diff,
    reviewed_edit_digest,
)
from agent_maintainer.ecosystems.java.semantic_edits import (
    SemanticEditRequest,
    SemanticEditResult,
    text_digest,
    validated_semantic_edit,
)
from agent_maintainer.ecosystems.java.templates.api import render_build_fragment, ruleset_text


class JavaSetupStatus(StrEnum):
    """Safe result states for Java setup planning."""

    READY = "ready"
    UNCHANGED = "unchanged"
    SEMANTIC_EDIT = "semantic-edit"
    REFUSED = "refused"


@dataclass(frozen=True)
class JavaSetupPlan:
    """Deterministic writes or one refused/semantic Java setup handoff."""

    root: Path
    status: JavaSetupStatus
    edits: tuple[ReviewedFileEdit, ...]
    semantic_edit: SemanticEditRequest | None
    reason: str
    review_digest: str


def plan_java_setup(root: Path, *, dsl: str | None = None) -> JavaSetupPlan:
    """Inspect a repository and return a non-mutating Java setup plan."""

    canonical_root = root.resolve(strict=True)
    selected = _selected_build(canonical_root, dsl=dsl)
    if isinstance(selected, str):
        return _plan(canonical_root, JavaSetupStatus.REFUSED, reason=selected)
    build_path, build_dsl = selected
    ruleset_edits = _ruleset_edits(canonical_root)
    if isinstance(ruleset_edits, str):
        return _plan(canonical_root, JavaSetupStatus.REFUSED, reason=ruleset_edits)
    build_edit = _build_edit(canonical_root, build_path, build_dsl)
    if isinstance(build_edit, SemanticEditRequest):
        return _plan(
            canonical_root,
            JavaSetupStatus.SEMANTIC_EDIT,
            edits=ruleset_edits,
            semantic_edit=build_edit,
            reason="existing Gradle build requires a reviewed semantic edit",
        )
    edits = (*build_edit, *ruleset_edits)
    status = JavaSetupStatus.READY if edits else JavaSetupStatus.UNCHANGED
    reason = "review deterministic Java setup edits" if edits else "Java setup already current"
    return _plan(canonical_root, status, edits=edits, reason=reason)


def preview_java_setup(plan: JavaSetupPlan) -> str:
    """Render the exact deterministic diff bound by ``plan.review_digest``."""

    if plan.status == JavaSetupStatus.REFUSED:
        raise SetupReviewError(plan.reason)
    if plan.status == JavaSetupStatus.SEMANTIC_EDIT:
        raise SetupReviewError("semantic edit result is required before a diff can be reviewed")
    return render_reviewed_diff(plan.edits)


def apply_java_setup(plan: JavaSetupPlan, *, approved_digest: str) -> tuple[Path, ...]:
    """Apply one deterministic Java setup plan after exact diff approval."""

    if plan.status not in {JavaSetupStatus.READY, JavaSetupStatus.UNCHANGED}:
        raise SetupReviewError(plan.reason)
    return apply_reviewed_edits(plan.root, plan.edits, approved_digest=approved_digest)


def apply_semantic_edit_result(
    plan: JavaSetupPlan,
    result: SemanticEditResult,
    *,
    approved_digest: str,
) -> tuple[Path, ...]:
    """Apply an agent-produced semantic edit only after validation and review."""

    request = plan.semantic_edit
    if plan.status != JavaSetupStatus.SEMANTIC_EDIT or request is None:
        raise SetupReviewError("plan does not contain a semantic edit request")
    edit = validated_semantic_edit(request, result)
    edits = (edit, *plan.edits)
    return apply_reviewed_edits(plan.root, edits, approved_digest=approved_digest)


def _selected_build(root: Path, *, dsl: str | None) -> tuple[str, str] | str:
    builds = tuple(name for name in ("build.gradle", "build.gradle.kts") if (root / name).exists())
    if len(builds) > 1:
        return "both Gradle DSL build files are present; refusing ambiguous setup"
    if builds:
        build_path = builds[0]
        return build_path, "kotlin" if build_path.endswith(".kts") else "groovy"
    selected_dsl = dsl or _settings_dsl(root) or "kotlin"
    if selected_dsl not in {"groovy", "kotlin"}:
        return f"unsupported Gradle DSL: {selected_dsl}"
    if selected_dsl == "kotlin":
        return "build.gradle.kts", "kotlin"
    return "build.gradle", "groovy"


def _settings_dsl(root: Path) -> str | None:
    groovy = (root / "settings.gradle").exists()
    kotlin = (root / "settings.gradle.kts").exists()
    if groovy and kotlin:
        return None
    if groovy:
        return "groovy"
    if kotlin:
        return "kotlin"
    return None


def _ruleset_edits(root: Path) -> tuple[ReviewedFileEdit, ...] | str:
    edits: list[ReviewedFileEdit] = []
    for name, path in (
        ("checkstyle", "config/checkstyle/checkstyle.xml"),
        ("pmd", "config/pmd/pmd.xml"),
    ):
        expected = ruleset_text(name)
        current = _read_optional(root / path)
        if current is None:
            edits.append(ReviewedFileEdit(path, None, expected, f"add curated {name} rules"))
        elif current != expected:
            return f"existing managed ruleset differs and will not be overwritten: {path}"
    return tuple(edits)


def _build_edit(
    root: Path,
    path: str,
    dsl: str,
) -> tuple[ReviewedFileEdit, ...] | SemanticEditRequest:
    expected = render_build_fragment(dsl)
    current = _read_optional(root / path)
    if current is None:
        return (ReviewedFileEdit(path, None, expected, "add pinned Java Gradle build"),)
    if current == expected:
        return ()
    if current == _recognized_scaffold(dsl):
        return (ReviewedFileEdit(path, current, expected, "expand recognized Java scaffold"),)
    return SemanticEditRequest(
        path=path,
        dsl=dsl,
        original_sha256=text_digest(current),
        required_elements=("pinned plugins", "Spotless", "SpotBugs", "Checkstyle", "PMD", "JaCoCo"),
        forbidden_changes=("preserve existing build behavior", "do not modify unrelated files"),
    )


def _recognized_scaffold(dsl: str) -> str:
    if dsl == "kotlin":
        return "plugins {\n    java\n}\n"
    return "plugins {\n    id 'java'\n}\n"


def _read_optional(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SetupReviewError(f"cannot safely read Java setup path {path.name}: {exc}") from exc


def _plan(
    root: Path,
    status: JavaSetupStatus,
    *,
    edits: tuple[ReviewedFileEdit, ...] = (),
    semantic_edit: SemanticEditRequest | None = None,
    reason: str,
) -> JavaSetupPlan:
    return JavaSetupPlan(
        root=root,
        status=status,
        edits=edits,
        semantic_edit=semantic_edit,
        reason=reason,
        review_digest=reviewed_edit_digest(edits),
    )
