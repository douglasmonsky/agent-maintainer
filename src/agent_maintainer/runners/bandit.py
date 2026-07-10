"""Run Bandit with JSON output preserved as a diagnostic artifact."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any

from agent_maintainer.core.config import load_config
from agent_maintainer.core.executor import command_env

BANDIT_JSON_NAME = "bandit.json"
BANDIT_FINDING_LIMIT = 50
BANDIT_ROOT_CONFIG = Path(".bandit")


def main() -> int:
    """Run Bandit using maintenance settings and write the JSON artifact."""

    config = load_config()
    output_dir = Path(config.diagnostic_artifacts_dir)
    return run_bandit(output_dir / BANDIT_JSON_NAME, package_paths=config.package_paths)


def run_bandit(json_output_path: Path, *, package_paths: tuple[str, ...]) -> int:
    """Run Bandit, persist valid JSON stdout, and print compact findings."""

    clear_stale_artifact(json_output_path)
    bandit = shutil.which("bandit") or "bandit"
    command = bandit_command(bandit, package_paths=package_paths)
    result = subprocess.run(  # nosec B603
        command,
        text=True,
        capture_output=True,
        env=command_env(),
        check=False,
    )
    findings = write_json_output(json_output_path, result.stdout)
    forward_output(result.stdout, result.stderr, findings)
    return result.returncode


def bandit_command(bandit: str, *, package_paths: tuple[str, ...]) -> list[str]:
    """Build the Bandit command with the conventional root policy when present."""

    command = [bandit, "-q", "-f", "json"]
    if BANDIT_ROOT_CONFIG.is_file():
        command.extend(("--ini", str(BANDIT_ROOT_CONFIG)))
    return [*command, "-r", *package_paths]


def clear_stale_artifact(path: Path) -> None:
    """Remove the previous JSON artifact before a new Bandit run."""

    path.unlink(missing_ok=True)


def write_json_output(path: Path, output: str) -> list[dict[str, Any]] | None:
    """Persist valid Bandit JSON stdout and return parsed findings."""

    if not output.strip():
        return None
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")
    raw_findings = payload.get("results", [])
    if not isinstance(raw_findings, list):
        return None
    return [item for item in raw_findings if isinstance(item, dict)]


def forward_output(
    stdout: str,
    stderr: str,
    findings: list[dict[str, Any]] | None,
) -> None:
    """Print compact Bandit findings, falling back to raw command output."""

    if findings is None:
        if stdout:
            print(stdout, end="")
    elif findings:
        print(format_findings(findings))
    if stderr:
        print(stderr, end="", file=sys.stderr)


def format_findings(findings: list[dict[str, Any]]) -> str:
    """Format Bandit JSON findings as concise editor-style lines."""

    lines = [format_finding(finding) for finding in findings[:BANDIT_FINDING_LIMIT]]
    omitted = len(findings) - len(lines)
    if omitted > 0:
        lines.append(f"... {omitted} more findings omitted. See .verify-logs/bandit.json")
    return "\n".join(lines)


def format_finding(finding: dict[str, Any]) -> str:
    """Return one compact Bandit finding line."""

    filename = finding.get("filename", "<unknown>")
    line_number = finding.get("line_number", 1)
    test_id = finding.get("test_id") or "BANDIT"
    severity = finding.get("issue_severity") or "UNKNOWN"
    confidence = finding.get("issue_confidence") or "UNKNOWN"
    text = finding.get("issue_text") or ""
    return f"{filename}:{line_number}: {test_id} {severity}/{confidence} {text}".rstrip()


if __name__ == "__main__":
    sys.exit(main())
