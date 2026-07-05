"""Command-backed tools exposed through the optional MCP server."""

from __future__ import annotations

import subprocess  # nosec B404
import sys
from pathlib import Path

from agent_maintainer.mcp.models import McpToolRequest, McpToolResult

VERIFY_TIMEOUT_SECONDS = 1_800


def verify_request(
    *,
    profile: str = "fast",
    base_ref: str | None = None,
    compare_branch: str | None = None,
    staged: bool = False,
    force: bool = False,
) -> McpToolRequest:
    """Build a bounded verifier request."""

    command = [*agent_maintainer_command("verify"), "--profile", profile]
    if base_ref:
        command.extend(("--base-ref", base_ref))
    if compare_branch:
        command.extend(("--compare-branch", compare_branch))
    if staged:
        command.append("--staged")
    if force:
        command.append("--force")
    return McpToolRequest(
        name="verify",
        description="Run an Agent Maintainer verification profile.",
        command=tuple(command),
        timeout_seconds=VERIFY_TIMEOUT_SECONDS,
    )


def context_failures_request(
    *,
    log_dir: str = ".verify-logs",
    limit: int = 10,
    check: str | None = None,
) -> McpToolRequest:
    """Build a bounded failure-context request."""

    command = [
        *agent_maintainer_command("context"),
        "--log-dir",
        log_dir,
        "failures",
        "--limit",
        str(limit),
        "--format",
        "json",
    ]
    if check:
        command.extend(("--check", check))
    return McpToolRequest(
        name="context_failures",
        description="Read recent bounded failure facts from verifier artifacts.",
        command=tuple(command),
    )


def context_pack_pointer_request(
    *,
    log_dir: str = ".verify-logs",
    check: str | None = None,
    base_ref: str = "HEAD",
    budget: int | None = None,
) -> McpToolRequest:
    """Build a context-pack pointer request without printing the full pack."""

    command = [
        *agent_maintainer_command("context"),
        "--log-dir",
        log_dir,
        "pack",
        "--base-ref",
        base_ref,
        "--format",
        "json",
    ]
    if check:
        command.extend(("--check", check))
    if budget is not None:
        command.extend(("--budget", str(budget)))
    return McpToolRequest(
        name="context_pack_pointer",
        description="Write a context pack and return a compact pointer.",
        command=tuple(command),
    )


def context_file_request(
    *,
    path: str,
    lines: str | None = None,
    symbol: str | None = None,
    around: int | None = None,
    context_lines: int | None = None,
) -> McpToolRequest:
    """Build a bounded file-context request."""

    command = [
        *agent_maintainer_command("context"),
        "file",
        path,
        "--format",
        "json",
    ]
    if lines:
        command.extend(("--lines", lines))
    if symbol:
        command.extend(("--symbol", symbol))
    if around is not None:
        command.extend(("--around", str(around)))
    if context_lines is not None:
        command.extend(("--context", str(context_lines)))
    return McpToolRequest(
        name="context_file",
        description="Read bounded source context for a file or symbol.",
        command=tuple(command),
    )


def events_summary_request(
    *,
    events_dir: str = ".verify-logs/events",
    limit: int = 10,
    summary: str = "summary",
) -> McpToolRequest:
    """Build a runtime-event summary request."""

    return McpToolRequest(
        name="events_summary",
        description="Summarize local Agent Maintainer runtime events.",
        command=tuple(
            [
                *agent_maintainer_command("events"),
                summary,
                "--events-dir",
                events_dir,
                "--limit",
                str(limit),
                "--format",
                "json",
            ],
        ),
    )


def attention_request(
    *,
    target: str = ".",
    limit: int = 10,
) -> McpToolRequest:
    """Build a request for the top attention-ranked files."""

    return McpToolRequest(
        name="attention",
        description="Read or build the attention ledger for high-risk files.",
        command=tuple(
            [
                *agent_maintainer_command("attention"),
                "--target",
                target,
                "top",
                "--limit",
                str(limit),
                "--format",
                "json",
            ],
        ),
    )


def docsync_check_request(
    *,
    base: str = "origin/main",
    config: str | None = None,
    trace: str | None = None,
) -> McpToolRequest:
    """Build a DocSync check request."""

    command = [sys.executable, "-m", "docsync", "check", "--base", base]
    if config:
        command.extend(("--config", config))
    if trace:
        command.extend(("--trace", trace))
    return McpToolRequest(
        name="docsync_check",
        description="Run DocSync traceability checks.",
        command=tuple(command),
    )


def run_tool_request(
    request: McpToolRequest,
    *,
    cwd: Path | None = None,
) -> McpToolResult:
    """Run a tool request and return bounded command output."""

    working_dir = Path.cwd() if cwd is None else cwd
    completed = subprocess.run(  # nosec B603
        request.command,
        cwd=working_dir,
        text=True,
        capture_output=True,
        timeout=request.timeout_seconds,
        check=False,
    )
    stdout, stdout_truncated = _bound_text(
        completed.stdout,
        limit=request.output_limit_chars,
    )
    stderr, stderr_truncated = _bound_text(
        completed.stderr,
        limit=request.output_limit_chars,
    )
    return McpToolResult(
        name=request.name,
        description=request.description,
        command=request.command,
        cwd=working_dir,
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
    )


def agent_maintainer_command(command: str) -> tuple[str, ...]:
    """Return a command using the current Python interpreter."""

    return (sys.executable, "-m", "agent_maintainer", command)


def _bound_text(text: str, *, limit: int) -> tuple[str, bool]:
    """Return text bounded from the end with a compact truncation marker."""

    if len(text) <= limit:
        return text, False
    marker = f"\n[output truncated to last {limit} characters]\n"
    keep = max(0, limit - len(marker))
    tail = text[-keep:]
    return f"{marker}{tail}", True
