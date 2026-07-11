"""Tests for the optional Agent Maintainer MCP surface."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from agent_maintainer.mcp import process as mcp_process
from agent_maintainer.mcp import server, tools
from agent_maintainer.mcp.models import McpToolResult
from tests.support.paths import REPO_ROOT

MISSING_DEPENDENCY_STATUS = 2


class FakeFastMCP:
    """Small FastMCP stand-in that records registered tools."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: dict[str, Callable[..., object]] = {}
        self.ran = False

    def tool(self) -> Callable[[Callable[..., object]], Callable[..., object]]:
        """Return a decorator matching FastMCP's tool registration shape."""

        def decorate(function: Callable[..., object]) -> Callable[..., object]:
            self.tools[function.__name__] = function
            return function

        return decorate

    def run(self) -> None:
        """Record that the server loop would start."""
        self.ran = True


def test_mcp_tool_requests_use_current_module_entrypoints() -> None:
    """Tool requests are backed by existing CLIs."""
    verify = tools.verify_request(
        workspace_root=REPO_ROOT,
        options=tools.VerifyRequestOptions(
            profile="precommit",
            base_ref="origin/main",
            compare_branch="HEAD",
            staged=True,
            force=True,
        ),
    )
    assert verify.command[:4] == (sys.executable, "-P", "-m", "agent_maintainer")
    assert verify.command[4:] == (
        "verify",
        "--profile",
        "precommit",
        "--base-ref",
        "origin/main",
        "--compare-branch",
        "HEAD",
        "--staged",
        "--force",
    )
    verify_environment = dict(verify.environment)
    assert verify_environment["AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR"].startswith(
        ".verify-logs/mcp/"
    )
    assert verify_environment["AGENT_MAINTAINER_RUNTIME_EVENTS_DIR"].endswith("/events")
    assert verify.generated_root == verify_environment["AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR"]

    failures = tools.context_failures_request(
        workspace_root=REPO_ROOT,
        check="pyright",
        limit=3,
    )
    assert failures.command[:5] == (
        sys.executable,
        "-P",
        "-m",
        "agent_maintainer",
        "context",
    )
    assert "failures" in failures.command
    assert "--format" in failures.command
    assert "json" in failures.command

    docsync = tools.docsync_check_request(
        workspace_root=REPO_ROOT,
        base="origin/main",
        config=".docsync/config.yml",
        trace=".docsync/trace.yml",
    )
    assert docsync.command == (
        sys.executable,
        "-P",
        "-m",
        "docsync",
        "check",
        "--base",
        "origin/main",
        "--config",
        ".docsync/config.yml",
        "--trace",
        ".docsync/trace.yml",
    )


def test_mcp_context_file_and_runtime_requests_are_bounded_json() -> None:
    """Context, event, and attention tools return bounded JSON commands."""
    context_file = tools.context_file_request(
        workspace_root=REPO_ROOT,
        options=tools.ContextFileRequestOptions(
            path="src/agent_maintainer/mcp/tools.py",
            lines="1:20",
            symbol="verify_request",
            around=10,
            context_lines=4,
        ),
    )
    assert context_file.command == (
        sys.executable,
        "-P",
        "-m",
        "agent_maintainer",
        "context",
        "file",
        "src/agent_maintainer/mcp/tools.py",
        "--format",
        "json",
        "--lines",
        "1:20",
        "--symbol",
        "verify_request",
        "--around",
        "10",
        "--context",
        "4",
    )

    events = tools.events_summary_request(
        workspace_root=REPO_ROOT,
        events_dir=".verify-logs/events",
        limit=2,
        summary="summary",
    )
    assert events.command == (
        sys.executable,
        "-P",
        "-m",
        "agent_maintainer",
        "events",
        "summary",
        "--events-dir",
        ".verify-logs/events",
        "--limit",
        "2",
        "--format",
        "json",
    )

    attention = tools.attention_request(
        workspace_root=REPO_ROOT,
        target=".",
        limit=3,
    )
    assert attention.command == (
        sys.executable,
        "-P",
        "-m",
        "agent_maintainer",
        "attention",
        "--target",
        ".",
        "top",
        "--limit",
        "3",
        "--format",
        "json",
    )


def test_context_pack_request_returns_pointer_not_full_pack_command() -> None:
    """MCP context packs must default to compact pointer output."""
    request = tools.context_pack_pointer_request(
        workspace_root=REPO_ROOT,
        check="pyright",
        budget=1000,
    )
    assert request.command[:5] == (
        sys.executable,
        "-P",
        "-m",
        "agent_maintainer",
        "context",
    )
    assert "pack" in request.command
    assert "--print-full" not in request.command
    assert "--format" not in request.command
    assert request.command[request.command.index("--compress") + 1] == "none"
    assert "--no-live-ratchet" in request.command


def test_run_tool_request_bounds_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Tool execution captures bounded output instead of leaking transcripts."""

    def fake_run(*args: object, **kwargs: object) -> mcp_process.BoundedProcessCapture:
        assert kwargs["cwd"] == tmp_path
        return _process_capture(
            returncode=1,
            stdout="x" * 20,
            stderr="y" * 20,
        )

    monkeypatch.setattr(mcp_process, "run_bounded_process", fake_run)
    request = tools.verify_request(
        workspace_root=tmp_path,
        options=tools.VerifyRequestOptions(profile="fast"),
    )
    short_request = request.__class__(
        name=request.name,
        description=request.description,
        command=request.command,
        output_limit_chars=12,
        hard_output_limit_bytes=request.hard_output_limit_bytes,
        timeout_seconds=request.timeout_seconds,
        environment=request.environment,
        generated_root=request.generated_root,
    )

    result = tools.run_tool_request(short_request, cwd=tmp_path)

    assert result.returncode == 1
    assert result.description == request.description
    assert result.stdout_truncated is True
    assert result.stderr_truncated is True
    assert len(result.stdout) == short_request.output_limit_chars
    assert len(result.stderr) == short_request.output_limit_chars
    assert result.stdout.endswith("x")
    assert result.stderr.endswith("y")


def test_run_tool_request_leaves_short_output_unmodified(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Short command output is returned without truncation markers."""

    def fake_run(*args: object, **kwargs: object) -> mcp_process.BoundedProcessCapture:
        return _process_capture(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(mcp_process, "run_bounded_process", fake_run)

    result = tools.run_tool_request(
        tools.verify_request(
            workspace_root=tmp_path,
            options=tools.VerifyRequestOptions(profile="fast"),
        ),
        cwd=tmp_path,
    )

    assert result.returncode == 0
    assert result.stdout == "ok"
    assert result.stderr == ""
    assert result.stdout_truncated is False
    assert result.stderr_truncated is False


def test_mcp_serve_help_does_not_require_optional_dependency() -> None:
    """The help path must work in core installs without the MCP extra."""
    result = subprocess.run(  # nosec B603
        [
            sys.executable,
            "-m",
            "agent_maintainer",
            "mcp",
            "serve",
            "--help",
        ],
        cwd=REPO_ROOT,
        env={
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Run Agent Maintainer MCP server" in result.stdout


def test_mcp_serve_missing_dependency_exits_with_install_hint(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Starting the server without MCP dependency returns actionable guidance."""

    def missing_fastmcp() -> type[object]:
        raise ModuleNotFoundError("mcp")

    monkeypatch.setattr(server, "_load_fastmcp", missing_fastmcp)

    assert server.main(["serve"]) == MISSING_DEPENDENCY_STATUS
    captured = capsys.readouterr()
    assert "agent-maintainer[mcp]" in captured.err


def test_mcp_serve_runs_loaded_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """Starting the server runs the loaded FastMCP server."""
    seen_servers: list[FakeFastMCP] = []

    def factory(name: str) -> FakeFastMCP:
        fast_mcp = FakeFastMCP(name)
        seen_servers.append(fast_mcp)
        return fast_mcp

    monkeypatch.setattr(server, "_load_fastmcp", lambda: factory)

    assert server.main(["serve"]) == 0
    assert seen_servers[0].ran is True
    assert "verify" in seen_servers[0].tools


def test_build_server_registers_expected_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """FastMCP registration stays limited to the Phase 156 surface."""

    def fake_run_tool_request(_request: object, *, cwd: Path | None = None) -> McpToolResult:
        return McpToolResult(
            name="fake",
            description="Fake tool.",
            command=("fake",),
            cwd=REPO_ROOT if cwd is None else cwd,
            returncode=0,
            stdout="ok",
            stderr="",
            stdout_truncated=False,
            stderr_truncated=False,
        )

    monkeypatch.setattr(tools, "run_tool_request", fake_run_tool_request)

    fake_server = server.build_server(FakeFastMCP, workspace_root=REPO_ROOT)

    assert fake_server.name == "agent-maintainer"
    assert set(fake_server.tools) == {
        "attention",
        "context_failures",
        "context_file",
        "context_pack_pointer",
        "docsync_check",
        "events_summary",
        "verify",
    }
    assert fake_server.tools["context_failures"]()["ok"] is True
    assert fake_server.tools["context_pack_pointer"]()["ok"] is True
    assert fake_server.tools["context_file"]("README.md")["ok"] is True
    assert fake_server.tools["events_summary"]()["ok"] is True
    assert fake_server.tools["attention"]()["ok"] is True
    assert fake_server.tools["docsync_check"]()["ok"] is True
    assert fake_server.tools["verify"]() == {
        "tool": "fake",
        "description": "Fake tool.",
        "ok": True,
        "returncode": 0,
        "command": ["fake"],
        "cwd": str(REPO_ROOT),
        "stdout": "ok",
        "stderr": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
        "timed_out": False,
        "stdout_limit_exceeded": False,
        "stderr_limit_exceeded": False,
    }


def _process_capture(
    *,
    returncode: int,
    stdout: str,
    stderr: str,
) -> mcp_process.BoundedProcessCapture:
    """Return one synthetic bounded-process result."""

    return mcp_process.BoundedProcessCapture(
        returncode=returncode,
        stdout=_stream_capture(stdout),
        stderr=_stream_capture(stderr),
    )


def _stream_capture(text: str) -> mcp_process.BoundedStreamCapture:
    """Return one complete synthetic stream capture."""

    payload = text.encode("utf-8")
    return mcp_process.BoundedStreamCapture(
        tail=payload,
        total_bytes=len(payload),
        truncated=False,
        limit_exceeded=False,
    )
