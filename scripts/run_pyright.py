"""Run Pyright with a generated project config from guardrail settings."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

from scripts.guardrail_config import GuardrailConfig, load_config
from scripts.guardrail_executor import command_env

PYRIGHT_CONFIG_PATH = Path(".verify-logs") / "pyrightconfig.generated.json"
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
    """Write the generated config, run Pyright, and forward its output."""

    config_path = write_pyright_config(PYRIGHT_CONFIG_PATH.parent, load_config())
    return run_pyright(config_path)


def write_pyright_config(directory: Path, config: GuardrailConfig) -> Path:
    """Write a Pyright config derived from guardrail roots and mode."""

    directory.mkdir(exist_ok=True)
    path = directory / PYRIGHT_CONFIG_PATH.name
    payload = {
        "include": unique_paths((*config.package_paths, *config.test_roots)),
        "exclude": list(PYRIGHT_EXCLUDES),
        "typeCheckingMode": config.pyright_type_checking_mode,
        "reportMissingTypeStubs": False,
    }
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")
    return path


def unique_paths(paths: tuple[str, ...]) -> list[str]:
    """Return configured paths once, preserving order."""

    seen: set[str] = set()
    unique: list[str] = []
    for path in paths:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def run_pyright(config_path: Path) -> int:
    """Run Pyright against a generated project config."""

    pyright = shutil.which("pyright") or "pyright"
    command = [pyright, "--project", str(config_path), "--outputjson"]
    result = subprocess.run(  # nosec B603
        command,
        text=True,
        capture_output=True,
        env=command_env(),
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
