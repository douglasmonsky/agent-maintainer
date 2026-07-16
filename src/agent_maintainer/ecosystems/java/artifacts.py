"""Bounded execution artifacts for Java/Gradle checks."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path

from agent_maintainer.core.artifact_environment import DIAGNOSTIC_ARTIFACTS_DIR_ENV
from agent_maintainer.ecosystems.java.provider import JavaGroup
from agent_maintainer.ecosystems.java.wrapper import ResolvedGradleWrapper

CONFIGURATION_EXIT_CODE = 2
MAX_ARTIFACT_BYTES = 32_768
MAX_ARTIFACT_TASKS = 128
MAX_ARTIFACT_TEXT = 128


def _bounded_text(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ")[:MAX_ARTIFACT_TEXT]


def sanitize_text(value: str, workspace: Path) -> str:
    """Remove workspace paths and line breaks from bounded artifact text."""
    return _bounded_text(value.replace(os.fspath(workspace), "<workspace>"))


def _encode_payload(payload: dict[str, object]) -> bytes:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"{rendered}\n".encode()


def write_artifact(path: Path, payload: dict[str, object]) -> None:
    """Atomically write one bounded Java execution artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _encode_payload(payload)
    if len(encoded) > MAX_ARTIFACT_BYTES:
        encoded = _encode_payload(_truncated_payload(payload))
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    with contextlib.ExitStack() as cleanup:
        cleanup.callback(temporary_path.unlink, missing_ok=True)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
        os.replace(temporary_path, path)


def _truncated_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": payload.get("schema_version", 1),
        "provider": "java-gradle",
        "group": payload.get("group", "unknown"),
        "profile": payload.get("profile", "unknown"),
        "status": payload.get("status", "artifact-truncated"),
        "exit_code": payload.get("exit_code", CONFIGURATION_EXIT_CODE),
        "reports_parsed": False,
        "evidence_status": "execution-only",
        "task_count": payload.get("task_count", 0),
        "artifact_truncated": True,
    }


def execution_payload(
    *,
    workspace: Path,
    wrapper: ResolvedGradleWrapper,
    gradle_args: tuple[str, ...],
    tasks: tuple[str, ...],
    exit_code: int,
) -> dict[str, object]:
    """Return bounded facts for one completed wrapper invocation."""
    bounded_tasks = [_bounded_text(task) for task in tasks[:MAX_ARTIFACT_TASKS]]
    return {
        "status": "passed" if exit_code == 0 else "gradle-failed",
        "exit_code": exit_code,
        "gradle_root": wrapper.gradle_root.relative_to(workspace).as_posix() or ".",
        "wrapper": wrapper.executable.relative_to(workspace).as_posix(),
        "gradle_args": [_bounded_text(value) for value in gradle_args],
        "task_count": len(tasks),
        "tasks": bounded_tasks,
        "tasks_truncated": len(tasks) > len(bounded_tasks),
    }


def base_payload(group: JavaGroup, profile: str) -> dict[str, object]:
    """Return the execution-only artifact envelope for one group."""
    return {
        "schema_version": 1,
        "provider": "java-gradle",
        "group": group,
        "profile": _bounded_text(profile),
        "status": "not-run",
        "exit_code": CONFIGURATION_EXIT_CODE,
        "reports_parsed": False,
        "evidence_status": "execution-only",
    }


def artifact_path(
    workspace: Path,
    group: JavaGroup,
    *,
    fallback_dir: str = ".verify-logs",
) -> Path:
    """Resolve the scoped artifact path for one Java check group."""
    configured = os.environ.get(DIAGNOSTIC_ARTIFACTS_DIR_ENV)
    artifacts_dir = Path(configured or fallback_dir)
    if not artifacts_dir.is_absolute():
        artifacts_dir = workspace / artifacts_dir
    return artifacts_dir.resolve(strict=False) / "java-gradle" / f"java-gradle-{group}.json"
