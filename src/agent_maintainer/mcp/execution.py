"""Execute validated MCP requests with isolated bounded children."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from agent_maintainer.mcp import path_safety
from agent_maintainer.mcp import process as mcp_process
from agent_maintainer.mcp.models import McpToolRequest, McpToolResult


def run_tool_request(
    request: McpToolRequest,
    *,
    cwd: Path | None = None,
) -> McpToolResult:
    """Run a validated tool request and return bounded command output."""

    working_dir = path_safety.resolve_workspace_root(Path.cwd() if cwd is None else cwd)
    completed = mcp_process.run_bounded_process(
        request.command,
        cwd=working_dir,
        environment=_isolated_python_environment(request.environment),
        options=mcp_process.BoundedProcessOptions(
            timeout_seconds=request.timeout_seconds,
            output_limit_chars=request.output_limit_chars,
            hard_output_limit_bytes=request.hard_output_limit_bytes,
        ),
    )
    stdout, stdout_truncated = _bound_text(
        completed.stdout.text(),
        limit=request.output_limit_chars,
    )
    stderr, stderr_truncated = _bound_text(
        completed.stderr.text(),
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
        stdout_truncated=stdout_truncated or completed.stdout.truncated,
        stderr_truncated=stderr_truncated or completed.stderr.truncated,
        generated_root=request.generated_root,
        timed_out=completed.timed_out,
        stdout_limit_exceeded=completed.stdout.limit_exceeded,
        stderr_limit_exceeded=completed.stderr.limit_exceeded,
    )


def python_module_command(module: str, *args: str) -> tuple[str, ...]:
    """Return an isolated command for one trusted installed Python module."""

    return (sys.executable, "-P", "-m", module, *args)


def _bound_text(text: str, *, limit: int) -> tuple[str, bool]:
    """Return text bounded from the end with a compact truncation marker."""

    if len(text) <= limit:
        return text, False
    if limit <= 0:
        return "", True
    marker = f"\n[output truncated to last {limit} characters]\n"
    if len(marker) >= limit:
        return text[-limit:], True
    keep = limit - len(marker)
    tail = text[-keep:]
    return f"{marker}{tail}", True


def _isolated_python_environment(
    request_environment: tuple[tuple[str, str], ...],
) -> dict[str, str]:
    """Return a child environment with one trusted Python import root."""

    environment = os.environ.copy()
    environment.update(dict(request_environment))
    for unsafe_name in ("PYTHONHOME", "PYTHONINSPECT", "PYTHONSTARTUP"):
        environment.pop(unsafe_name, None)
    environment["PYTHONSAFEPATH"] = "1"
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    return environment
