"""Command-backed tools exposed through the optional MCP server."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent_maintainer.mcp import execution, path_safety
from agent_maintainer.mcp.models import McpToolRequest, McpToolResult

VERIFY_TIMEOUT_SECONDS = 1_800
MIN_LIST_ITEMS = 1
MAX_LIST_ITEMS = 100
MIN_CONTEXT_PACK_BUDGET = 256
MAX_CONTEXT_PACK_BUDGET = 100_000
MIN_AROUND_LINE = 1
MAX_AROUND_LINE = 1_000_000
MIN_CONTEXT_LINES = 1
MAX_CONTEXT_LINES = 200
EventSummaryKind = Literal["summary", "failures", "slow-checks", "recent", "waste"]
EVENT_SUMMARY_KINDS = frozenset(("summary", "failures", "slow-checks", "recent", "waste"))


def run_tool_request(
    request: McpToolRequest,
    *,
    cwd: Path | None = None,
) -> McpToolResult:
    """Run one validated request through the bounded execution boundary."""

    return execution.run_tool_request(request, cwd=cwd)


@dataclass(frozen=True)
class VerifyRequestOptions:
    """Model-controlled options for one verifier request."""

    profile: str = "fast"
    base_ref: str | None = None
    compare_branch: str | None = None
    staged: bool = False
    force: bool = False


@dataclass(frozen=True)
class ContextFileRequestOptions:
    """Model-controlled options for one bounded file-context request."""

    path: str
    lines: str | None = None
    symbol: str | None = None
    around: int | None = None
    context_lines: int | None = None


def verify_request(
    *,
    workspace_root: Path,
    options: VerifyRequestOptions | None = None,
) -> McpToolRequest:
    """Build a bounded verifier request."""

    selected = options or VerifyRequestOptions()
    generated_root = path_safety.validate_generated_workspace_path(
        _unique_verifier_root(),
        workspace_root=workspace_root,
        label="MCP verifier artifact root",
        policy=path_safety.DIRECTORY_PATH,
    )
    events_root = str(Path(generated_root) / "events")
    path_safety.validate_generated_workspace_path(
        events_root,
        workspace_root=workspace_root,
        label="MCP verifier event root",
        policy=path_safety.DIRECTORY_PATH,
    )
    command = [*agent_maintainer_command("verify"), "--profile", selected.profile]
    if selected.base_ref:
        command.extend(("--base-ref", _validated_git_revision(selected.base_ref, label="base_ref")))
    if selected.compare_branch:
        command.extend(
            (
                "--compare-branch",
                _validated_git_revision(selected.compare_branch, label="compare_branch"),
            )
        )
    if selected.staged:
        command.append("--staged")
    if selected.force:
        command.append("--force")
    return McpToolRequest(
        name="verify",
        description="Run an Agent Maintainer verification profile.",
        command=tuple(command),
        timeout_seconds=VERIFY_TIMEOUT_SECONDS,
        environment=(
            ("AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR", generated_root),
            ("AGENT_MAINTAINER_RUNTIME_EVENTS_DIR", events_root),
        ),
        generated_root=generated_root,
    )


def context_failures_request(
    *,
    workspace_root: Path,
    log_dir: str = ".verify-logs",
    limit: int = 10,
    check: str | None = None,
) -> McpToolRequest:
    """Build a bounded failure-context request."""

    safe_log_dir = path_safety.validate_workspace_path(
        log_dir,
        workspace_root=workspace_root,
        label="log_dir",
        policy=path_safety.DIRECTORY_PATH,
    )
    safe_limit = _validated_bounded_int(
        limit,
        label="limit",
        minimum=MIN_LIST_ITEMS,
        maximum=MAX_LIST_ITEMS,
    )
    command = [
        *agent_maintainer_command("context"),
        "--log-dir",
        safe_log_dir,
        "failures",
        "--limit",
        str(safe_limit),
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
    workspace_root: Path,
    log_dir: str = ".verify-logs",
    check: str | None = None,
    base_ref: str = "HEAD",
    budget: int | None = None,
) -> McpToolRequest:
    """Build a context-pack pointer request without printing the full pack."""

    safe_base_ref = _validated_git_revision(base_ref, label="base_ref")
    safe_log_dir = path_safety.validate_generated_workspace_path(
        log_dir,
        workspace_root=workspace_root,
        label="log_dir",
        policy=path_safety.DIRECTORY_PATH,
    )
    context_dir = str(Path(safe_log_dir) / "context")
    path_safety.validate_workspace_path(
        context_dir,
        workspace_root=workspace_root,
        label="context pack output directory",
        policy=path_safety.DIRECTORY_PATH,
    )
    for output_name in ("PACK.md", "PACK.json"):
        path_safety.validate_workspace_path(
            str(Path(context_dir) / output_name),
            workspace_root=workspace_root,
            label=f"context pack output {output_name}",
            policy=path_safety.OUTPUT_FILE_PATH,
        )
    command = [
        *agent_maintainer_command("context"),
        "--log-dir",
        safe_log_dir,
        "pack",
        "--base-ref",
        safe_base_ref,
        "--compress",
        "none",
        "--no-live-ratchet",
    ]
    if check:
        command.extend(("--check", check))
    if budget is not None:
        safe_budget = _validated_bounded_int(
            budget,
            label="budget",
            minimum=MIN_CONTEXT_PACK_BUDGET,
            maximum=MAX_CONTEXT_PACK_BUDGET,
        )
        command.extend(("--budget", str(safe_budget)))
    return McpToolRequest(
        name="context_pack_pointer",
        description="Write a context pack and return a compact pointer.",
        command=tuple(command),
    )


def context_file_request(
    *,
    workspace_root: Path,
    options: ContextFileRequestOptions,
) -> McpToolRequest:
    """Build a bounded file-context request."""

    safe_path = path_safety.validate_workspace_path(
        options.path,
        workspace_root=workspace_root,
        label="path",
        policy=path_safety.CONTEXT_FILE_PATH,
    )
    command = [
        *agent_maintainer_command("context"),
        "file",
        safe_path,
        "--format",
        "json",
    ]
    if options.lines:
        command.extend(("--lines", options.lines))
    if options.symbol:
        command.extend(("--symbol", options.symbol))
    if options.around is not None:
        safe_around = _validated_bounded_int(
            options.around,
            label="around",
            minimum=MIN_AROUND_LINE,
            maximum=MAX_AROUND_LINE,
        )
        command.extend(("--around", str(safe_around)))
    if options.context_lines is not None:
        safe_context_lines = _validated_bounded_int(
            options.context_lines,
            label="context_lines",
            minimum=MIN_CONTEXT_LINES,
            maximum=MAX_CONTEXT_LINES,
        )
        command.extend(("--context", str(safe_context_lines)))
    return McpToolRequest(
        name="context_file",
        description="Read bounded source context for a file or symbol.",
        command=tuple(command),
    )


def events_summary_request(
    *,
    workspace_root: Path,
    events_dir: str = ".verify-logs/events",
    limit: int = 10,
    summary: EventSummaryKind = "summary",
) -> McpToolRequest:
    """Build a runtime-event summary request."""

    safe_events_dir = path_safety.validate_workspace_path(
        events_dir,
        workspace_root=workspace_root,
        label="events_dir",
        policy=path_safety.DIRECTORY_PATH,
    )
    safe_summary = _validated_event_summary(summary)
    safe_limit = _validated_bounded_int(
        limit,
        label="limit",
        minimum=MIN_LIST_ITEMS,
        maximum=MAX_LIST_ITEMS,
    )
    return McpToolRequest(
        name="events_summary",
        description="Summarize local Agent Maintainer runtime events.",
        command=tuple(
            [
                *agent_maintainer_command("events"),
                safe_summary,
                "--events-dir",
                safe_events_dir,
                "--limit",
                str(safe_limit),
                "--format",
                "json",
            ],
        ),
    )


def attention_request(
    *,
    workspace_root: Path,
    target: str = ".",
    limit: int = 10,
) -> McpToolRequest:
    """Build a request for the top attention-ranked files."""

    safe_target = path_safety.validate_workspace_path(
        target,
        workspace_root=workspace_root,
        label="target",
        policy=path_safety.EXISTING_DIRECTORY_PATH,
    )
    safe_limit = _validated_bounded_int(
        limit,
        label="limit",
        minimum=MIN_LIST_ITEMS,
        maximum=MAX_LIST_ITEMS,
    )
    return McpToolRequest(
        name="attention",
        description="Read or build the attention ledger for high-risk files.",
        command=tuple(
            [
                *agent_maintainer_command("attention"),
                "--target",
                safe_target,
                "top",
                "--limit",
                str(safe_limit),
                "--format",
                "json",
            ],
        ),
    )


def docsync_check_request(
    *,
    workspace_root: Path,
    base: str = "origin/main",
    config: str | None = None,
    trace: str | None = None,
) -> McpToolRequest:
    """Build a DocSync check request."""

    safe_base = _validated_git_revision(base, label="base")
    command = [*execution.python_module_command("docsync", "check"), "--base", safe_base]
    if config:
        safe_config = path_safety.validate_workspace_path(
            config,
            workspace_root=workspace_root,
            label="config",
            policy=path_safety.BOUNDED_INPUT_FILE_PATH,
        )
        command.extend(("--config", safe_config))
    if trace:
        safe_trace = path_safety.validate_workspace_path(
            trace,
            workspace_root=workspace_root,
            label="trace",
            policy=path_safety.BOUNDED_INPUT_FILE_PATH,
        )
        command.extend(("--trace", safe_trace))
    return McpToolRequest(
        name="docsync_check",
        description="Run DocSync traceability checks.",
        command=tuple(command),
    )


def agent_maintainer_command(command: str) -> tuple[str, ...]:
    """Return a command using the current Python interpreter."""

    return execution.python_module_command("agent_maintainer", command)


def _unique_verifier_root() -> str:
    """Return one repository-relative verifier artifact root."""

    return str(Path(".verify-logs/mcp") / uuid.uuid4().hex)


def _validated_git_revision(value: str, *, label: str) -> str:
    """Reject revision text that Git could interpret as an option."""

    if (
        not value
        or value.strip() != value
        or value.startswith("-")
        or any(character.isspace() or not character.isprintable() for character in value)
    ):
        raise ValueError(f"{label} must be a non-option Git revision without whitespace")
    return value


def _validated_event_summary(value: str) -> str:
    """Restrict MCP event access to bounded summary views."""

    if value not in EVENT_SUMMARY_KINDS:
        raise ValueError("summary must select a bounded runtime-event summary view")
    return value


def _validated_bounded_int(
    value: int,
    *,
    label: str,
    minimum: int,
    maximum: int,
) -> int:
    """Return one non-boolean integer inside its MCP contract bounds."""

    if isinstance(value, bool) or value < minimum or value > maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")
    return value
