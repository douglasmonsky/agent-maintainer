"""Doctor checks for context artifact retention policy."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.core import config as maintainer_config
from agent_maintainer.doctor.support.models import (
    DISABLED,
    OK,
    UNSAFE_CONFIG,
    WARNING,
    DoctorResult,
)

BROAD_VERIFY_LOG_UPLOAD_PATHS = frozenset(
    (
        ".verify-logs",
        ".verify-logs/",
        ".verify-logs/**",
    )
)
MIN_QUOTED_SCALAR_LENGTH = 2
YAML_QUOTE_CHARS = frozenset(("'", '"'))


def check_context_pack_upload_policy(
    repo_root: Path, config: maintainer_config.MaintainerConfig
) -> DoctorResult:
    """Report workflows that can upload local-only context packs."""

    if not config.diagnostic_artifacts_enabled:
        return DoctorResult(
            "context-pack-artifacts",
            OK,
            "Diagnostic artifacts are disabled.",
            state=DISABLED,
        )
    if not config.context_write_context_packs:
        return DoctorResult(
            "context-pack-artifacts",
            OK,
            "Context pack writing is disabled.",
            state=DISABLED,
        )
    if not config.context_packs_local_only or not config.context_pack_contains_source:
        return DoctorResult(
            "context-pack-artifacts",
            OK,
            "Context packs are not marked local-only source artifacts.",
        )

    unsafe_workflows = context_pack_upload_workflow_paths(repo_root)
    if unsafe_workflows:
        paths = ", ".join(unsafe_workflows)
        return DoctorResult(
            "context-pack-artifacts",
            WARNING,
            f"Workflow artifact upload can include local-only context packs: {paths}.",
            state=UNSAFE_CONFIG,
            hint=("Upload explicit safe .verify-logs files and exclude .verify-logs/context/**."),
        )

    return DoctorResult(
        "context-pack-artifacts",
        OK,
        "Workflow artifacts do not upload local-only context packs.",
    )


def context_pack_upload_workflow_paths(repo_root: Path) -> tuple[str, ...]:
    """Return workflow paths with broad .verify-logs artifact uploads."""

    workflow_dir = repo_root / ".github" / "workflows"
    if not workflow_dir.exists():
        return ()

    unsafe_paths: list[str] = []
    workflow_paths = sorted((*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")))
    for workflow_path in workflow_paths:
        try:
            workflow_text = workflow_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if workflow_uploads_broad_verify_logs(workflow_text):
            unsafe_paths.append(workflow_path.relative_to(repo_root).as_posix())
    return tuple(unsafe_paths)


def workflow_uploads_broad_verify_logs(workflow_text: str) -> bool:
    """Return whether upload-artifact can include the whole .verify-logs tree."""

    if "actions/upload-artifact" not in workflow_text:
        return False
    return any(line_has_broad_verify_logs_path(line) for line in workflow_text.splitlines())


def line_has_broad_verify_logs_path(line: str) -> bool:
    """Return whether a YAML path line targets the whole .verify-logs tree."""

    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    if "#" in stripped:
        stripped = stripped.split("#", 1)[0].rstrip()
    if stripped.startswith("path:"):
        value = stripped.removeprefix("path:").strip()
        return unquote_yaml_scalar(value) in BROAD_VERIFY_LOG_UPLOAD_PATHS
    return unquote_yaml_scalar(stripped) in BROAD_VERIFY_LOG_UPLOAD_PATHS


def unquote_yaml_scalar(value: str) -> str:
    """Remove simple quote wrapping from a YAML scalar."""

    if is_quoted_yaml_scalar(value):
        return value[1:-1]
    return value


def is_quoted_yaml_scalar(value: str) -> bool:
    """Return whether value has matching YAML quote characters."""

    if len(value) < MIN_QUOTED_SCALAR_LENGTH:
        return False
    quote = value[0]
    return quote in YAML_QUOTE_CHARS and value[-1] == quote
