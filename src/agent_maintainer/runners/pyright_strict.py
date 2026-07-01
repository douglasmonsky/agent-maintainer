"""Run strict Pyright as a baseline ratchet."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
import sys
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

from agent_maintainer.core.config import MaintainerConfig, load_config
from agent_maintainer.core.executor import command_env
from agent_maintainer.runners.pyright import (
    python_interpreter,
    write_json_output,
    write_pyright_config,
)

PYRIGHT_STRICT_CONFIG_NAME = "pyrightconfig.strict.generated.json"
PYRIGHT_STRICT_JSON_NAME = "pyright-strict.json"
UNKNOWN_RULE = "unknown-rule"
TOP_SUMMARY_LIMIT = 10


@dataclass(frozen=True)
class StrictPyrightStats:
    """Aggregated strict Pyright diagnostic counts."""

    total_errors: int
    files_analyzed: int
    by_rule: dict[str, int]
    by_file: dict[str, int]


@dataclass(frozen=True)
class StrictBaseline:
    """Committed strict Pyright baseline."""

    total_errors: int
    by_rule: dict[str, int]


@dataclass(frozen=True)
class StrictRatchetResult:
    """Strict Pyright comparison result."""

    passed: bool
    current: StrictPyrightStats
    baseline: StrictBaseline
    allowed_errors: int


def main() -> int:
    """Run strict Pyright and compare against configured baseline."""

    config = load_config()
    if not config.pyright_strict_ratchet_enabled:
        print("pyright strict ratchet skipped: disabled")
        return 0
    return run_strict_ratchet(config)


def run_strict_ratchet(config: MaintainerConfig) -> int:
    """Run strict Pyright and return ratchet exit code."""

    output_dir = Path(config.diagnostic_artifacts_dir)
    strict_config = strict_pyright_config(config)
    config_path = write_pyright_config(
        output_dir,
        strict_config,
        config_name=PYRIGHT_STRICT_CONFIG_NAME,
    )
    payload = run_pyright_json(config_path, output_dir / PYRIGHT_STRICT_JSON_NAME)
    if payload is None:
        return 1
    baseline = load_baseline(Path(config.pyright_strict_baseline))
    if baseline is None:
        return 1
    current = stats_from_payload(payload)
    if current.files_analyzed == 0:
        print("pyright strict analyzed 0 files; check generated project paths.")
        return 1
    result = compare_stats(
        current,
        baseline,
        extra_error_budget=config.pyright_strict_max_errors,
    )
    print(format_result(result))
    return 0 if result.passed else 1


def strict_pyright_config(config: MaintainerConfig) -> MaintainerConfig:
    """Return config copy forcing strict type checking."""

    return replace(config, pyright_type_checking_mode="strict")


def run_pyright_json(config_path: Path, output_path: Path) -> dict[str, Any] | None:
    """Run Pyright and return parsed JSON, preserving stdout artifact."""

    pyright = shutil.which("pyright") or "pyright"
    result = subprocess.run(  # nosec B603
        [
            pyright,
            "--project",
            str(config_path),
            "--pythonpath",
            python_interpreter(),
            "--outputjson",
        ],
        text=True,
        capture_output=True,
        env=command_env(),
        check=False,
    )
    write_json_output(output_path, result.stdout)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("pyright strict did not produce JSON output.")
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        return None
    if result.returncode not in {0, 1}:
        print(f"pyright strict failed with exit code {result.returncode}.")
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        return None
    if isinstance(payload, dict):
        return cast(dict[str, Any], payload)
    print("pyright strict JSON output was not an object.")
    return None


def load_baseline(path: Path) -> StrictBaseline | None:
    """Load committed strict Pyright baseline."""

    if not path.exists():
        print(f"pyright strict baseline missing: {path}")
        print("Repair: python -m pip install -e . and regenerate the baseline intentionally.")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"pyright strict baseline is not valid JSON: {path}")
        return None
    total_errors = payload.get("total_errors")
    by_rule_raw = payload.get("by_rule", {})
    if not isinstance(total_errors, int) or not isinstance(by_rule_raw, dict):
        print(f"pyright strict baseline has invalid shape: {path}")
        return None
    by_rule = baseline_rule_counts(cast(dict[str, object], by_rule_raw))
    if by_rule is None:
        print(f"pyright strict baseline has invalid rule counts: {path}")
        return None
    return StrictBaseline(
        total_errors=total_errors,
        by_rule=by_rule,
    )


def baseline_rule_counts(value: dict[str, object]) -> dict[str, int] | None:
    """Return typed baseline counts when all values are integers."""

    counts: dict[str, int] = {}
    for rule, count in value.items():
        if not isinstance(count, int):
            return None
        counts[str(rule)] = count
    return counts


def stats_from_payload(payload: dict[str, Any]) -> StrictPyrightStats:
    """Build strict diagnostic counts from Pyright JSON payload."""

    diagnostics = diagnostic_errors(payload)
    summary = summary_payload(payload)
    total_errors = summary.get("errorCount")
    files_analyzed = summary.get("filesAnalyzed")
    return StrictPyrightStats(
        total_errors=total_errors if isinstance(total_errors, int) else len(diagnostics),
        files_analyzed=files_analyzed if isinstance(files_analyzed, int) else 0,
        by_rule=count_by_rule(diagnostics),
        by_file=count_by_file(diagnostics),
    )


def diagnostic_errors(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return error diagnostics from Pyright JSON payload."""

    raw_diagnostics = payload.get("generalDiagnostics", [])
    if not isinstance(raw_diagnostics, list):
        return []
    diagnostics: list[dict[str, Any]] = []
    for diagnostic in cast(list[object], raw_diagnostics):
        if isinstance(diagnostic, dict):
            typed_diagnostic = cast(dict[str, Any], diagnostic)
            if typed_diagnostic.get("severity") == "error":
                diagnostics.append(typed_diagnostic)
    return diagnostics


def summary_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return summary object from Pyright JSON payload."""

    summary = payload.get("summary", {})
    if isinstance(summary, dict):
        return cast(dict[str, Any], summary)
    return {}


def count_by_rule(diagnostics: list[dict[str, Any]]) -> dict[str, int]:
    """Return error counts grouped by Pyright rule."""

    counter: Counter[str] = Counter(
        str(diagnostic.get("rule") or UNKNOWN_RULE) for diagnostic in diagnostics
    )
    return dict(counter)


def count_by_file(diagnostics: list[dict[str, Any]]) -> dict[str, int]:
    """Return error counts grouped by file path."""

    counter: Counter[str] = Counter(
        normalize_file(diagnostic.get("file")) for diagnostic in diagnostics
    )
    return dict(counter)


def normalize_file(file_value: object) -> str:
    """Return repo-relative file path when possible."""

    if not isinstance(file_value, str) or not file_value:
        return "<unknown>"
    path = Path(file_value)
    if not path.is_absolute():
        return file_value
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def compare_stats(
    current: StrictPyrightStats,
    baseline: StrictBaseline,
    *,
    extra_error_budget: int,
) -> StrictRatchetResult:
    """Compare current strict diagnostics against baseline."""

    allowed_errors = baseline.total_errors + extra_error_budget
    return StrictRatchetResult(
        passed=current.total_errors <= allowed_errors,
        current=current,
        baseline=baseline,
        allowed_errors=allowed_errors,
    )


def format_result(result: StrictRatchetResult) -> str:
    """Format compact strict Pyright ratchet result."""

    status = "passed" if result.passed else "failed"
    current_errors = result.current.total_errors
    baseline_errors = result.baseline.total_errors
    allowed_errors = result.allowed_errors
    files_analyzed = result.current.files_analyzed
    delta = current_errors - baseline_errors
    lines = [
        format_headline(status, current_errors, baseline_errors, allowed_errors, delta),
        f"files analyzed: {files_analyzed}",
        "top rules:",
        *format_top_counts(result.current.by_rule),
        "top files:",
        *format_top_counts(result.current.by_file),
    ]
    if not result.passed:
        lines.append("Repair: reduce strict diagnostics or intentionally lower the baseline.")
    return "\n".join(lines)


def format_headline(
    status: str,
    current_errors: int,
    baseline_errors: int,
    allowed_errors: int,
    delta: int,
) -> str:
    """Return strict ratchet headline."""

    delta_text = signed_number(delta)
    return " ".join(
        (
            f"pyright strict ratchet {status}:",
            f"{current_errors} errors",
            f"(baseline {baseline_errors},",
            f"allowed {allowed_errors},",
            f"delta {delta_text})",
        ),
    )


def signed_number(value: int) -> str:
    """Return integer with explicit sign for non-negative values."""

    if value >= 0:
        return f"+{value}"
    return str(value)


def format_top_counts(counts: dict[str, int]) -> list[str]:
    """Return compact top-count lines."""

    if not counts:
        return ["- none"]
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [f"- {name}: {count}" for name, count in ranked[:TOP_SUMMARY_LIMIT]]


if __name__ == "__main__":
    sys.exit(main())
