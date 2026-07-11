"""Bounded verifier log expansion helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent_context.failures import DEFAULT_CONTEXT_BUDGET, load_manifest
from agent_context.reading.file_safety import read_bounded_utf8_file
from agent_context.structured_values import json_object, json_objects

DEFAULT_TAIL_LINES = 120
TOKEN_CHAR_RATIO = 4
MAX_LOG_BYTES = 8_388_608


@dataclass(frozen=True)
class LogRequest:
    """Requested verifier log selection."""

    head: int | None = None
    tail: int | None = None
    line_range: str | None = None
    budget: int = DEFAULT_CONTEXT_BUDGET
    confirm_large: bool = False
    workspace_root: Path | None = None
    require_relative_manifest_paths: bool = True


@dataclass(frozen=True)
class LogSelection:
    """Selected verifier log context."""

    check_name: str
    log_path: Path
    text: str
    original_chars: int
    selected_chars: int
    omitted_lines: int
    refused: bool = False

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "check": self.check_name,
            "log_path": str(self.log_path),
            "text": self.text,
            "original_chars": self.original_chars,
            "selected_chars": self.selected_chars,
            "omitted_lines": self.omitted_lines,
            "refused": self.refused,
        }


def resolve_log_path(
    log_dir: Path,
    check_name: str,
    *,
    workspace_root: Path | None = None,
    require_relative_manifest_paths: bool = True,
) -> Path:
    """Return log path from manifest or conventional log filename."""

    root = _log_workspace_root(log_dir, workspace_root)
    manifest = load_manifest(log_dir)
    path = _manifest_log_path(manifest, check_name)
    if path is None:
        return log_dir / f"{check_name}.log"
    if require_relative_manifest_paths:
        _validate_manifest_path(path)
        return root / path
    return path if path.is_absolute() else Path.cwd() / path


def _manifest_log_path(manifest: object, check_name: str) -> Path | None:
    """Return the first matching log path from a manifest payload."""

    payload = json_object(manifest)
    if payload is None:
        return None
    for check in json_objects(payload.get("checks")):
        path = log_path_from_check(check, check_name)
        if path is not None:
            return path
    return None


def log_path_from_check(check: object, check_name: str) -> Path | None:
    """Return log path when manifest item matches check."""

    payload = json_object(check)
    if payload is None or payload.get("name") != check_name:
        return None
    log_path = payload.get("log_path")
    return Path(str(log_path)) if log_path else None


def select_log(
    log_dir: Path,
    check_name: str,
    request: LogRequest | None = None,
) -> LogSelection:
    """Return selected log content or a bounded refusal."""

    request = request or LogRequest()
    root = _log_workspace_root(log_dir, request.workspace_root)
    resolved = _selected_log_text(log_dir, check_name, request=request, workspace_root=root)
    if isinstance(resolved, LogSelection):
        return resolved
    path, text = resolved
    return _bounded_log_selection(check_name, path, text, request=request)


def _selected_log_text(
    log_dir: Path,
    check_name: str,
    *,
    request: LogRequest,
    workspace_root: Path,
) -> tuple[Path, str] | LogSelection:
    """Resolve and read one safe log, or return a terminal selection."""

    try:
        path = resolve_log_path(
            log_dir,
            check_name,
            workspace_root=workspace_root,
            require_relative_manifest_paths=request.require_relative_manifest_paths,
        )
    except ValueError as exc:
        return LogSelection(check_name, log_dir, f"Refused log context: {exc}", 0, 0, 0, True)
    safe_read = read_bounded_utf8_file(
        path,
        workspace_root=workspace_root,
        max_bytes=MAX_LOG_BYTES,
    )
    if safe_read.text is None:
        reason = safe_read.safety.reason
        if reason.startswith("unreadable:"):
            prefix = f"No log found for {check_name}"
            message = ": ".join((prefix, str(path)))
            return LogSelection(check_name, path, message, 0, 0, 0)
        message = f"Refused log context: {reason}"
        return LogSelection(check_name, path, message, 0, len(message), 0, True)
    return path, safe_read.text


def _bounded_log_selection(
    check_name: str,
    path: Path,
    text: str,
    *,
    request: LogRequest,
) -> LogSelection:
    """Slice and budget one already-read log."""

    selected, omitted_lines = slice_text(text, request)
    selected_chars = len(selected)
    original_chars = len(text)
    if selected_chars > request.budget and not request.confirm_large:
        estimate_command = estimate_log_command(check_name, request)
        refusal = refusal_message(selected_chars, request.budget, estimate_command)
        return LogSelection(
            check_name, path, refusal, original_chars, len(refusal), omitted_lines, True
        )
    if selected_chars > request.budget:
        bounded = selected[: request.budget].rstrip()
    else:
        bounded = selected.rstrip()
    if selected_chars > request.budget:
        omitted_chars = selected_chars - request.budget
        bounded = f"{bounded}\n... log output omitted {omitted_chars} chars."
    return LogSelection(check_name, path, bounded, original_chars, len(bounded), omitted_lines)


def _log_workspace_root(log_dir: Path, workspace_root: Path | None) -> Path:
    """Return the explicit workspace, or the explicit absolute log directory."""

    if workspace_root is not None:
        return workspace_root.resolve()
    return log_dir.resolve().parent if log_dir.is_absolute() else Path.cwd().resolve()


def _validate_manifest_path(path: Path) -> None:
    """Reject manifest-controlled absolute and traversal log paths."""

    if path.is_absolute():
        raise ValueError("manifest log_path must be workspace-relative")
    if ".." in path.parts:
        raise ValueError("manifest log_path must not contain parent traversal")


def slice_text(
    text: str,
    request: LogRequest,
) -> tuple[str, int]:
    """Return selected log text and omitted line count."""

    lines = text.splitlines()
    if request.line_range:
        return slice_line_range(lines, request.line_range)
    if request.head is not None and request.tail is not None:
        return slice_head_tail(lines, request.head, request.tail)
    if request.head is not None:
        return join_selection(lines[: request.head], len(lines) - min(request.head, len(lines)))
    selected_tail = request.tail if isinstance(request.tail, int) else DEFAULT_TAIL_LINES
    return join_selection(lines[-selected_tail:], max(0, len(lines) - selected_tail))


def slice_line_range(lines: list[str], line_range: str) -> tuple[str, int]:
    """Return one-based inclusive line range."""

    start_raw, end_raw = line_range.split(":", maxsplit=1)
    start = max(1, int(start_raw))
    end = max(start, int(end_raw))
    offset = start - 1
    selected = lines[offset:end]
    omitted = max(0, len(lines) - len(selected))
    return ("\n".join(selected), omitted)


def slice_head_tail(lines: list[str], head: int, tail: int) -> tuple[str, int]:
    """Return head and tail sections with omission marker."""

    head_lines = lines[:head]
    tail_lines = lines[-tail:] if tail else []
    omitted = max(0, len(lines) - len(head_lines) - len(tail_lines))
    selected = [*head_lines, f"... {omitted} lines omitted ...", *tail_lines] if omitted else lines
    return ("\n".join(selected), omitted)


def join_selection(lines: list[str], omitted_lines: int) -> tuple[str, int]:
    """Return joined selected lines and omitted count."""

    return ("\n".join(lines), max(0, omitted_lines))


def estimate_log_command(check_name: str, request: LogRequest) -> str:
    """Return matching log estimate command."""

    pieces = ["python", "-m", "agent_maintainer", "context", "estimate", "--log", check_name]
    if request.head is not None:
        pieces.extend(("--head", str(request.head)))
    if request.tail is not None:
        pieces.extend(("--tail", str(request.tail)))
    if request.line_range is not None:
        pieces.extend(("--lines", request.line_range))
    return " ".join(pieces)


def refusal_message(requested_chars: int, budget: int, estimate_command: str) -> str:
    """Return bounded refusal for large log output."""

    tokens = (requested_chars + TOKEN_CHAR_RATIO - 1) // TOKEN_CHAR_RATIO
    return (
        f"Requested output is approximately {requested_chars:,} characters. "
        f"Estimated tokens: ~{tokens}. "
        f"Default budget is {budget:,} characters. "
        f"Estimate first: {estimate_command}. "
        "Safer options: --tail 120, --lines 1:120, or --budget "
        f"{requested_chars} --confirm-large."
    )


def render_log_text(selection: LogSelection) -> str:
    """Return text log report."""

    return "\n".join(
        (
            f"Context log: {selection.check_name}",
            f"Log: {selection.log_path}",
            f"Original chars: {selection.original_chars}",
            f"Omitted lines: {selection.omitted_lines}",
            "",
            selection.text,
        )
    ).rstrip()


def render_log_json(selection: LogSelection) -> str:
    """Return stable JSON log report."""

    return json.dumps(selection.to_json(), indent=2, sort_keys=True)
