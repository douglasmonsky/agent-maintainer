"""Run Pyright with a generated project config from maintenance settings."""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

from agent_maintainer.core.config import MaintainerConfig, load_config
from agent_maintainer.core.executor import command_env

PYRIGHT_CONFIG_NAME = "pyrightconfig.generated.json"
PYRIGHT_JSON_NAME = "pyright.json"
PYRIGHT_EXCLUDES = (
    ".git",
    ".venv",
    "venv",
    "build",
    "dist",
    "node_modules",
    ".tox",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache",
)


def main() -> int:
    """Write config, run Pyright, and forward output."""

    config = load_config()
    output_dir = Path(config.diagnostic_artifacts_dir)
    config_path = write_pyright_config(output_dir, config)
    return run_pyright(config_path, output_dir / PYRIGHT_JSON_NAME)


def write_pyright_config(
    directory: Path,
    config: MaintainerConfig,
    *,
    config_name: str = PYRIGHT_CONFIG_NAME,
) -> Path:
    """Write a Pyright config derived from maintainer roots and mode."""

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / config_name
    repo_root = Path.cwd()
    payload = {
        "include": relative_config_paths(
            directory, repo_root, (*config.package_paths, *config.test_roots)
        ),
        "exclude": relative_config_paths(directory, repo_root, PYRIGHT_EXCLUDES),
        "extraPaths": relative_config_paths(directory, repo_root, (".", "src")),
        "typeCheckingMode": config.pyright_type_checking_mode,
        "reportMissingTypeStubs": False,
    }
    path.write_text(
        f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )
    return path


def relative_config_paths(
    config_directory: Path, repo_root: Path, paths: tuple[str, ...]
) -> list[str]:
    """Return paths relative to the generated Pyright config directory."""

    start = config_directory.resolve()
    return unique_paths(
        tuple(
            os.path.relpath((repo_root / configured_path).resolve(), start=start)
            for configured_path in paths
        )
    )


def unique_paths(paths: tuple[str, ...]) -> list[str]:
    """Return configured paths once, preserving order."""

    seen: set[str] = set()
    unique: list[str] = []
    for path in paths:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def run_pyright(config_path: Path, json_output_path: Path | None = None) -> int:
    """Run Pyright against a project config."""

    pyright = shutil.which("pyright") or "pyright"
    command = [
        pyright,
        "--project",
        str(config_path),
        "--pythonpath",
        python_interpreter(),
        "--outputjson",
    ]
    result = subprocess.run(  # nosec B603
        command,
        text=True,
        capture_output=True,
        env=command_env(),
        check=False,
    )
    write_json_output(json_output_path, result.stdout)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode == 0 and analyzed_file_count(result.stdout) == 0:
        print(
            "Pyright analyzed 0 files; check generated project paths.",
            file=sys.stderr,
        )
        return 1
    return result.returncode


def python_interpreter() -> str:
    """Return the project Python interpreter Pyright should inspect."""

    for candidate in (Path(".venv/bin/python"), Path("venv/bin/python")):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def analyzed_file_count(output: str) -> int | None:
    """Return Pyright analyzed file count when output is JSON."""

    if not output.strip():
        return None
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        summary = payload.get("summary")
        if isinstance(summary, dict):
            files_analyzed = summary.get("filesAnalyzed")
            if isinstance(files_analyzed, int):
                return files_analyzed
    return None


def write_json_output(path: Path | None, output: str) -> None:
    """Persist Pyright JSON stdout when a destination is configured."""

    if path is None or not output.strip():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
