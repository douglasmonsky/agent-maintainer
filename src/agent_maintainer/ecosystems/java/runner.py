"""Hermetic command-only runner for grouped Java/Gradle checks."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from agent_maintainer.config.loader import load_config
from agent_maintainer.ecosystems.java.provider import (
    JavaGroup,
    JavaProviderConfigurationError,
    plan_group,
)
from agent_maintainer.ecosystems.java.wrapper import (
    GradleWrapperError,
    ResolvedGradleWrapper,
    resolve_gradle_wrapper,
)

VERIFY_PROFILE_ENV = "_AGENT_MAINTAINER_VERIFY_PROFILE"
ARTIFACTS_DIR_ENV = "AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR"
CONFIGURATION_EXIT_CODE = 2
MAX_ARTIFACT_BYTES = 32_768
MAX_ARTIFACT_TASKS = 128
MAX_ARTIFACT_TEXT = 128


def main(argv: list[str] | None = None) -> int:
    """Run one configured Gradle group and return its policy exit status."""
    args = _parser().parse_args(argv)
    group: JavaGroup = args.group
    workspace = Path.cwd().resolve(strict=True)
    profile = os.environ.get(VERIFY_PROFILE_ENV, "")
    artifact_path = _artifact_path(workspace, group)
    payload = _base_payload(group, profile)

    try:
        if not profile:
            raise JavaProviderConfigurationError(
                f"{VERIFY_PROFILE_ENV} is required for profile-aware Java task planning"
            )
        config = load_config(workspace)
        if ARTIFACTS_DIR_ENV not in os.environ:
            artifact_path = _artifact_path(
                workspace,
                group,
                fallback_dir=config.diagnostic_artifacts_dir,
            )
        tasks = plan_group(config.java, group, profile)
        if not tasks:
            raise JavaProviderConfigurationError(
                f"Java group '{group}' has no selected tasks for profile '{profile}'"
            )
        wrapper = resolve_gradle_wrapper(workspace, config.java.gradle_root)
        command = [
            os.fspath(wrapper.executable),
            *config.java.gradle_args,
            *tasks,
        ]
        completed = subprocess.run(
            command,
            cwd=wrapper.gradle_root,
            shell=False,
            check=False,
        )
        exit_code = completed.returncode
        payload.update(
            _execution_payload(
                workspace=workspace,
                wrapper=wrapper,
                gradle_args=config.java.gradle_args,
                tasks=tasks,
                exit_code=exit_code,
            )
        )
    except (
        GradleWrapperError,
        JavaProviderConfigurationError,
        OSError,
        TypeError,
        tomllib.TOMLDecodeError,
    ) as exc:
        exit_code = CONFIGURATION_EXIT_CODE
        payload.update(
            status="configuration-error",
            exit_code=exit_code,
            error=_sanitize_text(str(exc), workspace),
        )

    try:
        _write_artifact(artifact_path, payload)
    except OSError as exc:
        print(_sanitize_text(f"could not write Java artifact: {exc}", workspace), file=sys.stderr)
        return CONFIGURATION_EXIT_CODE
    return exit_code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one Java/Gradle verification group")
    parser.add_argument("--group", required=True, choices=("format", "static", "tests"))
    return parser


def _artifact_path(
    workspace: Path,
    group: JavaGroup,
    *,
    fallback_dir: str = ".verify-logs",
) -> Path:
    configured = os.environ.get(ARTIFACTS_DIR_ENV)
    artifacts_dir = Path(configured or fallback_dir)
    if not artifacts_dir.is_absolute():
        artifacts_dir = workspace / artifacts_dir
    return artifacts_dir.resolve(strict=False) / "java-gradle" / f"java-gradle-{group}.json"


def _base_payload(group: JavaGroup, profile: str) -> dict[str, Any]:
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


def _execution_payload(
    *,
    workspace: Path,
    wrapper: ResolvedGradleWrapper,
    gradle_args: tuple[str, ...],
    tasks: tuple[str, ...],
    exit_code: int,
) -> dict[str, Any]:
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


def _bounded_text(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ")[:MAX_ARTIFACT_TEXT]


def _sanitize_text(value: str, workspace: Path) -> str:
    return _bounded_text(value.replace(os.fspath(workspace), "<workspace>"))


def _write_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _encode_payload(payload)
    if len(encoded) > MAX_ARTIFACT_BYTES:
        encoded = _encode_payload(
            {
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
        )
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _encode_payload(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


if __name__ == "__main__":
    raise SystemExit(main())
