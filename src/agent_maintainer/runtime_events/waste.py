"""Detect local runtime-event signals that waste agent time and tokens."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent_maintainer.runtime_events.read import RuntimeEventReadResult

HEAVY_PROFILES = frozenset(("full", "ci", "security", "manual"))
MIN_HEAVY_PROFILE_OVERLAP = 3
GENERATED_SIGNAL_LIMIT = 10
MEASUREMENT_LIMITATIONS = (
    "wait-poll counts require wait command runtime events",
    "agent narration patterns require aggregate conversation telemetry",
    "heredoc and chained-shell edit patterns require command-shape events",
    "same-state duplication requires verifier fingerprint events",
)
GENERATED_DIR_NAMES = frozenset(("__pycache__", "mutants", ".semgrep"))
GENERATED_SUFFIXES = (".pyc",)
DUPLICATE_NAME_MARKERS = (" 2", " copy")
GENERATED_CLEANUP_HINT = "inspect listed paths; remove only verified generated/cache files"


def _empty_rows() -> list[dict[str, object]]:
    return []


@dataclass(frozen=True)
class RuntimeEventWasteReport:
    """Compact measurable and not-yet-measurable cadence waste."""

    files_read: int
    total_events: int
    malformed_lines: int
    signals: list[dict[str, object]] = field(default_factory=_empty_rows)
    limitations: tuple[str, ...] = MEASUREMENT_LIMITATIONS

    def to_payload(self) -> dict[str, object]:
        """Return JSON-serializable waste report payload."""
        return {
            "files_read": self.files_read,
            "total_events": self.total_events,
            "malformed_lines": self.malformed_lines,
            "signals": self.signals,
            "limitations": list(self.limitations),
        }

    def to_json(self) -> str:
        """Return deterministic JSON representation."""
        return json.dumps(self.to_payload(), indent=2, sort_keys=True)


def summarize_runtime_waste(
    read_result: RuntimeEventReadResult,
    *,
    repo_root: Path | None = None,
) -> RuntimeEventWasteReport:
    """Return compact cadence-waste signals from local runtime events."""
    records = read_result.records
    signals: list[dict[str, object]] = []
    signals.extend(_repeated_profile_signals(records))
    signals.extend(_profile_overlap_signals(records))
    signals.extend(_fresh_reuse_signal(records))
    signals.extend(_failed_command_signal(records))
    if repo_root is not None:
        signals.extend(_generated_artifact_signals(repo_root))
    return RuntimeEventWasteReport(
        files_read=read_result.files_read,
        total_events=len(records),
        malformed_lines=read_result.malformed_lines,
        signals=signals,
    )


def render_waste_text(report: RuntimeEventWasteReport) -> str:
    """Render compact text cadence-waste report."""
    lines = [
        "Runtime Event Waste Report",
        f"Events: {report.total_events} across {report.files_read} file(s)",
        f"Malformed lines: {report.malformed_lines}",
        "Measured signals:",
    ]
    if report.signals:
        lines.extend(f"- {_signal_text(signal)}" for signal in report.signals)
    else:
        lines.append("- none measured")
    lines.append("Not yet measurable:")
    lines.extend(f"- {limitation}" for limitation in report.limitations)
    return "\n".join(lines)


def _repeated_profile_signals(records: list[dict[str, Any]]) -> list[dict[str, object]]:
    profile_counts = _profile_counts(records)
    return [
        {
            "signal": "repeated-profile",
            "profile": profile,
            "count": count,
            "severity": "warning",
            "message": f"{profile} ran {count} times in sampled event window",
        }
        for profile, count in sorted(profile_counts.items())
        if count > 1
    ]


def _profile_overlap_signals(records: list[dict[str, Any]]) -> list[dict[str, object]]:
    profile_counts = _profile_counts(records)
    signals: list[dict[str, object]] = []
    if profile_counts["full"] and profile_counts["ci"]:
        signals.append(
            _overlap_signal(
                "full-ci-overlap",
                "full and ci both ran; use one broad profile unless overlap is under test",
            ),
        )
    if profile_counts["security"] and profile_counts["manual"]:
        signals.append(
            _overlap_signal(
                "security-manual-overlap",
                "security and manual both ran; reserve for releases or gate changes",
            ),
        )
    heavy_count = sum(1 for profile in HEAVY_PROFILES if profile_counts[profile])
    if heavy_count >= MIN_HEAVY_PROFILE_OVERLAP:
        signals.append(
            _overlap_signal(
                "three-heavy-profiles",
                f"{heavy_count} heavy profiles ran in sampled event window",
            ),
        )
    return signals


def _fresh_reuse_signal(records: list[dict[str, Any]]) -> list[dict[str, object]]:
    fresh_runs = _event_name_count(records, "verifier.fresh")
    reused_runs = _event_name_count(records, "verifier.reused")
    if fresh_runs <= 1 or reused_runs:
        return []
    return [
        {
            "signal": "fresh-run-only",
            "count": fresh_runs,
            "severity": "info",
            "message": "multiple fresh verifier runs were observed with no reuse events",
        },
    ]


def _failed_command_signal(records: list[dict[str, Any]]) -> list[dict[str, object]]:
    failed_commands = Counter(
        str(record.get("command"))
        for record in records
        if record.get("event_name") == "command.finished"
        and record.get("status") == "fail"
        and record.get("command")
    )
    return [
        {
            "signal": "repeated-command-failure",
            "command": command,
            "count": count,
            "severity": "warning",
            "message": f"{command} failed {count} times in sampled event window",
        }
        for command, count in sorted(failed_commands.items())
        if count > 1
    ]


def _generated_artifact_signals(repo_root: Path) -> list[dict[str, object]]:
    paths = _generated_artifact_paths(repo_root)
    if not paths:
        return []
    return [
        {
            "signal": "generated-artifact-debris",
            "severity": "warning",
            "count": len(paths),
            "message": (
                "generated/cache artifacts found; clean them instead of letting "
                "agents read or commit them"
            ),
            "paths": [path.as_posix() for path in paths[:GENERATED_SIGNAL_LIMIT]],
            "cleanup_hint": GENERATED_CLEANUP_HINT,
        },
    ]


def _generated_artifact_paths(repo_root: Path) -> list[Path]:
    ignored_dirs = {".git", ".venv", "venv", "node_modules", ".verify-logs"}
    matches: list[Path] = []
    for path in repo_root.rglob("*"):
        relative = path.relative_to(repo_root)
        if _ignored_path(relative, ignored_dirs):
            continue
        if _generated_artifact_path(path, relative):
            matches.append(relative)
    return sorted(matches)


def _ignored_path(path: Path, ignored_dirs: set[str]) -> bool:
    return any(part in ignored_dirs for part in path.parts)


def _generated_artifact_path(path: Path, relative: Path) -> bool:
    if path.is_dir():
        return path.name in GENERATED_DIR_NAMES
    if _inside_generated_dir(relative):
        return False
    return path.is_file() and _generated_file_name(path.name)


def _inside_generated_dir(path: Path) -> bool:
    return any(part in GENERATED_DIR_NAMES for part in path.parts[:-1])


def _generated_file_name(name: str) -> bool:
    return name.endswith(GENERATED_SUFFIXES) or any(
        marker in name for marker in DUPLICATE_NAME_MARKERS
    )


def _profile_counts(records: list[dict[str, Any]]) -> Counter[str]:
    return Counter(
        str(record.get("profile"))
        for record in records
        if record.get("event_name") == "profile.finished" and record.get("profile")
    )


def _event_name_count(records: list[dict[str, Any]], event_name: str) -> int:
    return sum(1 for record in records if record.get("event_name") == event_name)


def _overlap_signal(signal: str, message: str) -> dict[str, object]:
    return {"signal": signal, "severity": "warning", "message": message}


def _signal_text(signal: dict[str, object]) -> str:
    parts = [
        str(signal.get("signal", "unknown")),
        _optional_part("severity", signal.get("severity")),
        _optional_part("profile", signal.get("profile")),
        _optional_part("command", signal.get("command")),
        _optional_part("count", signal.get("count")),
        str(signal.get("message", "")),
        _paths_part(signal.get("paths")),
        _optional_part("cleanup", signal.get("cleanup_hint")),
    ]
    return " ".join(part for part in parts if part)


def _paths_part(value: object) -> str:
    if not isinstance(value, list) or not value:
        return ""
    paths = ", ".join(str(path) for path in value[:GENERATED_SIGNAL_LIMIT])
    return f"paths={paths}"


def _optional_part(label: str, value: object) -> str:
    if value in {"", None}:
        return ""
    return f"{label}={value}"
