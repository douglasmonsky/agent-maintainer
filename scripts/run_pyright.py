"""Run Pyright with a generated project config from guardrail settings."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

from scripts.guardrail_config import GuardrailConfig, load_config
from scripts.guardrail_executor import command_env

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
    """Write the generated config, run Pyright, and forward its output."""

    config = load_config()
    output_dir = Path(config.diagnostic_artifacts_dir)
    config_path = write_pyright_config(output_dir, config)
    return run_pyright(config_path, output_dir / PYRIGHT_JSON_NAME)


def write_pyright_config(directory: Path, config: GuardrailConfig) -> Path:
    """Write a Pyright config derived from guardrail roots and mode."""

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / PYRIGHT_CONFIG_NAME
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


def run_pyright(config_path: Path, json_output_path: Path | None = None) -> int:
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
    write_json_output(json_output_path, result.stdout)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def write_json_output(path: Path | None, output: str) -> None:
    """Persist Pyright JSON stdout when a destination is configured."""

    if path is None or not output.strip():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
