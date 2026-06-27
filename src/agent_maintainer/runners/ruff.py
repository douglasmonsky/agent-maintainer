"""Run Ruff with JSON output preserved as a diagnostic artifact."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any

from agent_maintainer.core.config import load_config
from agent_maintainer.core.executor import command_env

RUFF_JSON_NAME = "ruff.json"
RUFF_DIAGNOSTIC_LIMIT = 50


def main() -> int:
    """Run Ruff using maintenance settings and write the JSON artifact."""

    config = load_config()
    output_dir = Path(config.diagnostic_artifacts_dir)
    return run_ruff(output_dir / RUFF_JSON_NAME, max_complexity=config.ruff_max_complexity)


def run_ruff(json_output_path: Path, *, max_complexity: int) -> int:
    """Run Ruff, persist valid JSON stdout, and print compact diagnostics."""

    clear_stale_artifact(json_output_path)
    ruff = shutil.which("ruff") or "ruff"
    command = [
        ruff,
        "check",
        "--output-format=json",
        "--config",
        f"lint.mccabe.max-complexity={max_complexity}",
        ".",
    ]
    result = subprocess.run(  # nosec B603
        command,
        text=True,
        capture_output=True,
        env=command_env(),
        check=False,
    )
    diagnostics = write_json_output(json_output_path, result.stdout)
    forward_output(result.stdout, result.stderr, diagnostics)
    return result.returncode


def clear_stale_artifact(path: Path) -> None:
    """Remove the previous JSON artifact before a new Ruff run."""

    path.unlink(missing_ok=True)


def write_json_output(path: Path, output: str) -> list[dict[str, Any]] | None:
    """Persist valid Ruff JSON stdout and return parsed diagnostics."""

    if not output.strip():
        return None
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")
    return [item for item in payload if isinstance(item, dict)]


def forward_output(
    stdout: str,
    stderr: str,
    diagnostics: list[dict[str, Any]] | None,
) -> None:
    """Print compact Ruff diagnostics, falling back to raw command output."""

    if diagnostics is None:
        if stdout:
            print(stdout, end="")
    elif diagnostics:
        print(format_diagnostics(diagnostics))
    if stderr:
        print(stderr, end="", file=sys.stderr)


def format_diagnostics(diagnostics: list[dict[str, Any]]) -> str:
    """Format Ruff JSON diagnostics as concise editor-style lines."""

    lines = [format_diagnostic(diagnostic) for diagnostic in diagnostics[:RUFF_DIAGNOSTIC_LIMIT]]
    omitted = len(diagnostics) - len(lines)
    if omitted > 0:
        lines.append(f"... {omitted} more diagnostics omitted. See .verify-logs/ruff.json")
    return "\n".join(lines)


def format_diagnostic(diagnostic: dict[str, Any]) -> str:
    """Return one compact Ruff diagnostic line."""

    location = diagnostic.get("location", {})
    row = location.get("row", 1) if isinstance(location, dict) else 1
    column = location.get("column", 1) if isinstance(location, dict) else 1
    filename = diagnostic.get("filename", "<unknown>")
    code = diagnostic.get("code") or "RUF"
    message = diagnostic.get("message") or ""
    return f"{filename}:{row}:{column}: {code} {message}".rstrip()


if __name__ == "__main__":
    sys.exit(main())
