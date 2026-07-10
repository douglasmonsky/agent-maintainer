"""Adversarial tests for the MCP repository path boundary."""

from __future__ import annotations

import inspect
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from agent_maintainer.context import cli as context_cli
from agent_maintainer.context.pack import cli as pack_cli
from agent_maintainer.context.pack import ratchet as pack_ratchet
from agent_maintainer.mcp import path_safety, server, tools
from agent_maintainer.mcp.models import McpToolResult


def test_context_file_rejects_absolute_and_outside_paths_before_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Absolute and traversal paths never reach the command runner."""

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    inside = workspace / "inside.py"
    inside.write_text("safe = True\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside_secret = "OUTSIDE-CANARY-CONTENT"
    outside.write_text(outside_secret, encoding="utf-8")
    service = server.McpService.create(workspace)
    calls: list[object] = []

    def forbidden_run(*args: object, **kwargs: object) -> SimpleNamespace:
        calls.append((args, kwargs))
        raise AssertionError("unsafe request reached subprocess.run")

    monkeypatch.setattr(subprocess, "run", forbidden_run)

    for unsafe_path in (str(inside), "../outside.txt"):
        with pytest.raises(ValueError) as raised:
            service.context_file(unsafe_path)
        assert outside_secret not in str(raised.value)
    assert calls == []


@pytest.mark.parametrize(
    "sensitive_path",
    (
        ".docker/config.json",
        ".env",
        ".env.local",
        ".envrc",
        ".git-credentials",
        ".kube/config",
        "auth.json",
        "client_secret_123.json",
        "credentials.yml",
        "keys/id_ed25519",
        "keys/private-key.pem",
        "kubeconfig",
        "secret.json",
        "secrets.yaml",
        "terraform.tfstate.backup",
        "terraform.tfvars",
        "token.json",
    ),
)
def test_context_file_rejects_sensitive_names_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sensitive_path: str,
) -> None:
    """Credential and private-key names are refused without an open attempt."""

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(os, "open", _forbidden_open)

    with pytest.raises(ValueError, match="sensitive path"):
        tools.context_file_request(
            workspace_root=workspace,
            options=tools.ContextFileRequestOptions(path=sensitive_path),
        )


def test_context_file_rejects_symlink_parent_escape(tmp_path: Path) -> None:
    """A repository symlink cannot redirect file reads outside the root."""

    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / "canary.txt").write_text("secret", encoding="utf-8")
    (workspace / "redirect").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        tools.context_file_request(
            workspace_root=workspace,
            options=tools.ContextFileRequestOptions(path="redirect/canary.txt"),
        )


def test_context_file_rejects_sparse_oversized_file_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A sparse file beyond the byte ceiling is refused from metadata alone."""

    oversized = tmp_path / "oversized.txt"
    with oversized.open("wb") as stream:
        stream.seek(path_safety.MAX_CONTEXT_FILE_BYTES)
        stream.write(b"x")
    monkeypatch.setattr(os, "open", _forbidden_open)

    with pytest.raises(ValueError, match="byte limit"):
        tools.context_file_request(
            workspace_root=tmp_path,
            options=tools.ContextFileRequestOptions(path=oversized.name),
        )


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO support is POSIX-only")
def test_context_file_rejects_fifo_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A FIFO is classified from lstat and never opened or blocked on."""

    fifo = tmp_path / "input.pipe"
    os.mkfifo(fifo)
    monkeypatch.setattr(os, "open", _forbidden_open)

    with pytest.raises(ValueError, match="regular file"):
        tools.context_file_request(
            workspace_root=tmp_path,
            options=tools.ContextFileRequestOptions(path=fifo.name),
        )


def test_context_file_rejects_device_path_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Device paths are absolute and rejected before any open call."""

    monkeypatch.setattr(os, "open", _forbidden_open)

    with pytest.raises(ValueError, match="relative"):
        tools.context_file_request(
            workspace_root=tmp_path,
            options=tools.ContextFileRequestOptions(path="/dev/zero"),
        )


@pytest.mark.parametrize(
    "request_factory",
    (
        lambda root: tools.context_failures_request(
            workspace_root=root,
            log_dir="../logs",
        ),
        lambda root: tools.context_pack_pointer_request(
            workspace_root=root,
            log_dir="../logs",
        ),
        lambda root: tools.events_summary_request(
            workspace_root=root,
            events_dir="../events",
        ),
        lambda root: tools.attention_request(
            workspace_root=root,
            target="../repository",
        ),
        lambda root: tools.docsync_check_request(
            workspace_root=root,
            config="../config.yml",
        ),
        lambda root: tools.docsync_check_request(
            workspace_root=root,
            trace="../trace.json",
        ),
    ),
)
def test_every_mcp_filesystem_argument_rejects_traversal(
    tmp_path: Path,
    request_factory: Callable[[Path], object],
) -> None:
    """Every model-controlled filesystem argument shares the root policy."""

    with pytest.raises(ValueError, match="parent traversal"):
        request_factory(tmp_path)


def test_service_captures_workspace_root_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changing process cwd cannot widen an already-created service root."""

    workspace = tmp_path / "workspace"
    other = tmp_path / "other"
    workspace.mkdir()
    other.mkdir()
    (workspace / "source.py").write_text("value = 1\n", encoding="utf-8")
    (other / "other-only.py").write_text("outside = True\n", encoding="utf-8")
    service = server.McpService.create(workspace)
    observed: list[tuple[tuple[str, ...], Path]] = []

    def fake_run(request: tools.McpToolRequest, *, cwd: Path | None = None) -> McpToolResult:
        assert cwd is not None
        observed.append((request.command, cwd))
        return McpToolResult(
            name=request.name,
            description=request.description,
            command=request.command,
            cwd=cwd,
            returncode=0,
            stdout="{}",
            stderr="",
            stdout_truncated=False,
            stderr_truncated=False,
        )

    monkeypatch.setattr(tools, "run_tool_request", fake_run)
    monkeypatch.chdir(other)

    result = service.context_file("source.py", lines="1:1")

    assert result["ok"] is True
    assert observed[0][1] == workspace.resolve()
    assert "source.py" in observed[0][0]
    with pytest.raises(ValueError, match="does not exist"):
        service.context_file("other-only.py")


def test_context_pack_mcp_surface_has_no_file_injection_argument() -> None:
    """The MCP pack pointer cannot inject arbitrary file expansion paths."""

    parameters = inspect.signature(server.McpService.context_pack_pointer).parameters

    assert "files" not in parameters
    assert "file" not in parameters


def test_context_pack_mcp_rejects_source_tree_as_generated_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MCP cannot redirect pack output onto a regular workspace directory."""

    workspace = tmp_path / "workspace"
    source_dir = workspace / "context"
    source_dir.mkdir(parents=True)
    canary = source_dir / "PACK.md"
    canary.write_text("source canary\n", encoding="utf-8")
    monkeypatch.setattr(subprocess, "run", _forbidden_subprocess)

    with pytest.raises(ValueError, match=r"must remain under \.verify-logs"):
        server.McpService.create(workspace).context_pack_pointer(log_dir=".")

    assert canary.read_text(encoding="utf-8") == "source canary\n"


def test_context_pack_mcp_command_emits_pointer_not_full_pack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The MCP command omits selected log content from its child stdout."""

    workspace = tmp_path / "workspace"
    log_dir = workspace / ".verify-logs"
    log_dir.mkdir(parents=True)
    canary = "FULL-PACK-LOG-CANARY"
    (log_dir / "ruff.log").write_text(f"{canary}\n", encoding="utf-8")
    (log_dir / "manifest.json").write_text(
        '{"checks":[{"name":"ruff","status":"failed","exit_code":1,'
        '"log_path":".verify-logs/ruff.log"}]}',
        encoding="utf-8",
    )
    baseline = workspace / ".agent-maintainer" / "ratchet-baseline.json"
    baseline.parent.mkdir()
    baseline.write_text("{}", encoding="utf-8")
    request = tools.context_pack_pointer_request(workspace_root=workspace, check="ruff")

    def forbidden_ratchet(*args: object, **kwargs: object) -> object:
        raise AssertionError("MCP pack reached live ratchet scan")

    monkeypatch.setattr(
        pack_cli,
        "load_config",
        lambda: SimpleNamespace(
            context_compression_backend="headroom",
            context_compression_enabled=True,
            context_compression_require_backend=True,
            context_compression_target_ratio=0.5,
            context_max_failure_items=5,
            context_pack_budget_chars=1_000,
            ratchet_baseline_path=".agent-maintainer/ratchet-baseline.json",
            ratchet_target_limit=3,
        ),
    )
    monkeypatch.setattr(pack_ratchet, "status_report", forbidden_ratchet)
    monkeypatch.chdir(workspace)

    assert context_cli.main(list(request.command[5:])) == 0

    output = capsys.readouterr().out
    assert canary not in output
    assert ".verify-logs/context/PACK.md" in output
    assert request.command[-2:] == ("--check", "ruff")
    assert request.command[request.command.index("--compress") + 1] == "none"


@pytest.mark.parametrize(
    ("method_name", "keyword"),
    (
        ("verify", "base_ref"),
        ("context_pack_pointer", "base_ref"),
        ("docsync_check", "base"),
    ),
)
def test_mcp_rejects_git_option_injection_before_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    keyword: str,
) -> None:
    """Model-controlled revisions cannot turn Git options into outside writes."""

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("unchanged\n", encoding="utf-8")
    calls: list[object] = []

    def forbidden_run(*args: object, **kwargs: object) -> SimpleNamespace:
        calls.append((args, kwargs))
        raise AssertionError("unsafe revision reached subprocess.run")

    monkeypatch.setattr(subprocess, "run", forbidden_run)
    method = getattr(server.McpService.create(workspace), method_name)

    with pytest.raises(ValueError, match="non-option Git revision"):
        method(**{keyword: f"--output={outside}"})

    assert calls == []
    assert outside.read_text(encoding="utf-8") == "unchanged\n"


def test_events_summary_rejects_raw_export_before_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The compact MCP summary tool cannot invoke the raw event exporter."""

    monkeypatch.setattr(subprocess, "run", _forbidden_subprocess)

    with pytest.raises(ValueError, match="bounded runtime-event summary"):
        server.McpService.create(tmp_path).events_summary(
            summary=cast(tools.EventSummaryKind, "export"),
        )


def test_docsync_trace_requires_existing_nonsensitive_input(tmp_path: Path) -> None:
    """MCP treats a DocSync trace as a bounded input rather than an output."""

    with pytest.raises(ValueError, match="does not exist"):
        tools.docsync_check_request(workspace_root=tmp_path, trace="missing.yml")

    (tmp_path / "token.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="sensitive path"):
        tools.docsync_check_request(workspace_root=tmp_path, trace="token.json")


def test_context_pack_rejects_symlinked_output_directory_before_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pack output directory cannot redirect writes outside the workspace."""

    workspace = tmp_path / "workspace"
    log_dir = workspace / ".verify-logs"
    outside = tmp_path / "outside"
    log_dir.mkdir(parents=True)
    outside.mkdir()
    canary = outside / "PACK.md"
    canary.write_text("OUTSIDE-WRITE-CANARY", encoding="utf-8")
    (log_dir / "context").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(subprocess, "run", _forbidden_subprocess)

    with pytest.raises(ValueError, match="symlink"):
        server.McpService.create(workspace).context_pack_pointer()

    assert canary.read_text(encoding="utf-8") == "OUTSIDE-WRITE-CANARY"


def test_verify_rejects_symlinked_generated_root_before_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repository state cannot redirect MCP verifier artifacts outside the root."""

    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (workspace / ".verify-logs").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(subprocess, "run", _forbidden_subprocess)

    with pytest.raises(ValueError, match="symlink"):
        server.McpService.create(workspace).verify()

    assert list(outside.iterdir()) == []


def _forbidden_open(*args: object, **kwargs: object) -> int:
    """Fail when a refusal path attempts to open a filesystem object."""

    raise AssertionError(f"unexpected open: {args!r} {kwargs!r}")


def _forbidden_subprocess(*args: object, **kwargs: object) -> SimpleNamespace:
    """Fail if an unsafe request reaches process execution."""

    raise AssertionError(f"unexpected subprocess: {args!r} {kwargs!r}")
