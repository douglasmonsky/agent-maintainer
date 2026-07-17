"""Typed review and validation for agent-produced Gradle semantic edits."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from agent_maintainer.core.setup_plans import (
    ReviewedFileEdit,
    SetupReviewError,
    render_reviewed_diff,
    reviewed_edit_digest,
)


@dataclass(frozen=True)
class SemanticEditRequest:
    """Typed handoff for an agent to edit one arbitrary Gradle build semantically."""

    path: str
    dsl: str
    original_sha256: str
    required_elements: tuple[str, ...]
    forbidden_changes: tuple[str, ...]


@dataclass(frozen=True)
class SemanticEditValidation:
    """Validation evidence returned with an agent-produced semantic edit."""

    passed: bool
    details: tuple[str, ...]


@dataclass(frozen=True)
class SemanticEditResult:
    """Exact semantic-edit result that can be diffed and separately approved."""

    path: str
    original_text: str
    updated_text: str
    validation: SemanticEditValidation


def _validate_semantic_identity(
    request: SemanticEditRequest,
    result: SemanticEditResult,
) -> None:
    if result.path != request.path:
        raise SetupReviewError("semantic edit result targets an unexpected path")
    if text_digest(result.original_text) != request.original_sha256:
        raise SetupReviewError("semantic edit result does not match the requested source")


def _validate_semantic_content(result: SemanticEditResult) -> None:
    if not result.validation.passed:
        raise SetupReviewError("semantic edit validation failed")
    if result.updated_text == result.original_text:
        raise SetupReviewError("semantic edit result contains no change")


def validated_semantic_edit(
    request: SemanticEditRequest,
    result: SemanticEditResult,
) -> ReviewedFileEdit:
    """Return one reviewed edit after semantic-result validation."""

    _validate_semantic_identity(request, result)
    _validate_semantic_content(result)
    return ReviewedFileEdit(
        result.path,
        result.original_text,
        result.updated_text,
        "apply validated semantic Java setup edit",
    )


def preview_semantic_edit_result(
    request: SemanticEditRequest,
    result: SemanticEditResult,
    *,
    additional_edits: tuple[ReviewedFileEdit, ...] = (),
) -> str:
    """Validate and render an agent-produced semantic edit for review."""

    edit = validated_semantic_edit(request, result)
    validation = "\n".join(f"validation: {detail}" for detail in result.validation.details)
    return f"{validation}\n{render_reviewed_diff((edit, *additional_edits))}"


def semantic_edit_result_digest(
    request: SemanticEditRequest,
    result: SemanticEditResult,
    *,
    additional_edits: tuple[ReviewedFileEdit, ...] = (),
) -> str:
    """Return the digest of a validated semantic edit result."""

    edit = validated_semantic_edit(request, result)
    return reviewed_edit_digest((edit, *additional_edits))


def text_digest(text: str) -> str:
    """Return a stable digest for semantic-edit source identity."""

    return hashlib.sha256(text.encode()).hexdigest()
