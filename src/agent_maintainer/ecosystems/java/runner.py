"""Hermetic command-only runner for grouped Java/Gradle checks."""

from __future__ import annotations

import argparse
import os

# Security: this module executes only a repository-confined checked wrapper.
import subprocess  # nosec B404
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.config import loader
from agent_maintainer.core import artifact_environment
from agent_maintainer.ecosystems.java import artifacts, errors, provider, wrapper


@dataclass(frozen=True)
class RunOutcome:
    """Artifact path, payload, and exit status for one grouped execution."""

    artifact_path: Path
    payload: dict[str, object]
    exit_code: int


def main(argv: list[str] | None = None) -> int:
    """Run one configured Gradle group and return its policy exit status."""
    args = _parser().parse_args(argv)
    group: provider.JavaGroup = args.group
    workspace = Path.cwd().resolve(strict=True)
    profile = os.environ.get(artifact_environment.VERIFY_PROFILE_ENV, "")
    try:
        outcome = _run_group(workspace, group, profile)
    except (errors.JavaConfigurationError, OSError) as exc:
        outcome = _configuration_error_outcome(workspace, group, profile, exc)
    return _write_outcome(outcome, workspace)


def _run_group(workspace: Path, group: provider.JavaGroup, profile: str) -> RunOutcome:
    if not profile:
        profile_field = artifact_environment.VERIFY_PROFILE_ENV
        raise provider.JavaProviderConfigurationError(
            f"{profile_field} is required for profile-aware Java task planning"
        )
    config = _load_java_config(workspace)
    tasks = provider.plan_group(config.java, group, profile)
    if not tasks:
        raise provider.JavaProviderConfigurationError(
            f"Java group '{group}' has no selected tasks for profile '{profile}'"
        )
    resolved_wrapper = wrapper.resolve_gradle_wrapper(workspace, config.java.gradle_root)
    exit_code = _run_wrapper(
        resolved_wrapper.executable,
        resolved_wrapper.gradle_root,
        config.java.gradle_args,
        tasks,
    )
    payload = artifacts.base_payload(group, profile)
    payload.update(
        artifacts.execution_payload(
            workspace=workspace,
            wrapper=resolved_wrapper,
            gradle_args=config.java.gradle_args,
            tasks=tasks,
            exit_code=exit_code,
        )
    )
    return RunOutcome(
        artifacts.artifact_path(workspace, group, fallback_dir=config.diagnostic_artifacts_dir),
        payload,
        exit_code,
    )


def _load_java_config(workspace: Path):
    try:
        return loader.load_config(workspace)
    except (TypeError, tomllib.TOMLDecodeError) as exc:
        raise errors.JavaConfigurationError(str(exc)) from exc


def _run_wrapper(
    executable: Path,
    gradle_root: Path,
    gradle_args: tuple[str, ...],
    tasks: tuple[str, ...],
) -> int:
    command = [os.fspath(executable), *gradle_args, *tasks]
    # Security: executable confinement and argv validation happen before this call.
    completed = subprocess.run(  # nosec B603
        command,
        cwd=gradle_root,
        shell=False,
        check=False,
    )
    return completed.returncode


def _configuration_error_outcome(
    workspace: Path,
    group: provider.JavaGroup,
    profile: str,
    exc: Exception,
) -> RunOutcome:
    payload = artifacts.base_payload(group, profile)
    payload.update(
        status="configuration-error",
        exit_code=artifacts.CONFIGURATION_EXIT_CODE,
        error=artifacts.sanitize_text(str(exc), workspace),
    )
    return RunOutcome(
        artifacts.artifact_path(workspace, group),
        payload,
        artifacts.CONFIGURATION_EXIT_CODE,
    )


def _write_outcome(outcome: RunOutcome, workspace: Path) -> int:
    try:
        artifacts.write_artifact(outcome.artifact_path, outcome.payload)
    except OSError as exc:
        message = artifacts.sanitize_text(f"could not write Java artifact: {exc}", workspace)
        print(message, file=sys.stderr)
        return artifacts.CONFIGURATION_EXIT_CODE
    return outcome.exit_code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one Java/Gradle verification group")
    parser.add_argument("--group", required=True, choices=("format", "static", "tests"))
    return parser


if __name__ == "__main__":
    sys.exit(main())
