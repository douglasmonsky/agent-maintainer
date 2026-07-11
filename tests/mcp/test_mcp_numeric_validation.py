"""Tests fail-closed numeric validation for MCP requests."""

from collections.abc import Callable
from pathlib import Path

import pytest

from agent_maintainer.mcp import server, tools

OVER_MAX_LIST = 101
BELOW_MIN_BUDGET = 255
OVER_MAX_BUDGET = 100_001
OVER_MAX_LINE = 1_000_001
OVER_MAX_CONTEXT = 201


def _context_failures_zero(root: Path) -> object:
    return tools.context_failures_request(workspace_root=root, limit=0)


def _context_failures_bool(root: Path) -> object:
    return tools.context_failures_request(workspace_root=root, limit=True)


def _events_summary_negative(root: Path) -> object:
    return tools.events_summary_request(workspace_root=root, limit=-1)


def _events_summary_unbounded(root: Path) -> object:
    return tools.events_summary_request(workspace_root=root, limit=OVER_MAX_LIST)


def _attention_zero(root: Path) -> object:
    return tools.attention_request(workspace_root=root, limit=0)


def _context_pack_below_minimum(root: Path) -> object:
    return tools.context_pack_pointer_request(workspace_root=root, budget=BELOW_MIN_BUDGET)


def _context_pack_above_maximum(root: Path) -> object:
    return tools.context_pack_pointer_request(workspace_root=root, budget=OVER_MAX_BUDGET)


def test_attention_rejects_unbounded_limit(tmp_path: Path) -> None:
    """The MCP attention view cannot request the complete scored ledger."""

    with pytest.raises(ValueError, match="between 1 and 100"):
        server.McpService.create(tmp_path).attention(limit=OVER_MAX_LIST)


@pytest.mark.parametrize(
    "request_factory",
    (
        _context_failures_zero,
        _context_failures_bool,
        _events_summary_negative,
        _events_summary_unbounded,
        _attention_zero,
        _context_pack_below_minimum,
        _context_pack_above_maximum,
    ),
)
def test_numeric_arguments_fail_closed(
    tmp_path: Path,
    request_factory: Callable[[Path], object],
) -> None:
    """Invalid numeric values stop request construction before execution."""

    with pytest.raises(ValueError, match="must be between"):
        request_factory(tmp_path)


@pytest.mark.parametrize(
    "options",
    (
        tools.ContextFileRequestOptions(path="source.py", around=0),
        tools.ContextFileRequestOptions(path="source.py", around=True),
        tools.ContextFileRequestOptions(path="source.py", around=OVER_MAX_LINE),
        tools.ContextFileRequestOptions(path="source.py", context_lines=0),
        tools.ContextFileRequestOptions(path="source.py", context_lines=OVER_MAX_CONTEXT),
    ),
)
def test_file_windows_fail_closed(
    tmp_path: Path,
    options: tools.ContextFileRequestOptions,
) -> None:
    """Invalid file-window values never reach the context CLI."""

    (tmp_path / "source.py").write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must be between"):
        tools.context_file_request(workspace_root=tmp_path, options=options)
