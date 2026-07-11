"""Select bounded untrusted logs and file outlines for context packs."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from agent_context import failures as context_failures
from agent_context import sanitize
from agent_context.reading import files as file_reader
from agent_context.reading import logs as log_reader
from agent_maintainer.core.structured_values import json_array, json_object

DEFAULT_PACK_LOG_TAIL = 120
MIN_CONTEXT_ITEM_BUDGET = 800
MAX_CONTEXT_ITEM_BUDGET = 4_000


def payload_expansion_commands(payload: dict[str, object]) -> list[str]:
    """Return payload expansion commands."""

    commands = json_array(payload.get("expansion_commands"))
    if commands is None:
        return []
    return [str(command) for command in commands]


def payload_omitted_counts(payload: dict[str, object]) -> dict[str, int]:
    """Return payload omitted counts."""

    counts = json_object(payload.get("omitted_counts"))
    if counts is None:
        return {}
    return {key: value for key, value in counts.items() if isinstance(value, int)}


def log_payloads(
    log_dir: Path,
    total_budget: int,
    records: tuple[context_failures.FailureRecord, ...],
    *,
    check: str | None,
) -> list[dict[str, object]]:
    """Return bounded selected verifier log payloads."""

    names = selected_log_names(records, check=check)
    budget = item_budget(total_budget, max(len(names), 1))
    return [log_payload(log_dir, name, budget) for name in names]


def selected_log_names(
    records: tuple[context_failures.FailureRecord, ...],
    *,
    check: str | None,
) -> tuple[str, ...]:
    """Return check names whose logs should be included."""

    if records:
        return unique_names(record.name for record in records)
    if check:
        return (check,)
    return ()


def log_payload(log_dir: Path, check_name: str, budget: int) -> dict[str, object]:
    """Return bounded log payload for one check."""

    selection = log_reader.select_log(
        log_dir,
        check_name,
        log_reader.LogRequest(tail=DEFAULT_PACK_LOG_TAIL, budget=budget, confirm_large=True),
    )
    return {
        "check": selection.check_name,
        "source": str(selection.log_path),
        "text": sanitize.sanitize_text(selection.text),
        "untrusted": True,
        "original_chars": selection.original_chars,
        "selected_chars": selection.selected_chars,
        "omitted_lines": selection.omitted_lines,
        "refused": selection.refused,
    }


def file_payloads(files: tuple[Path, ...], total_budget: int) -> list[dict[str, object]]:
    """Return bounded requested file outline payloads."""

    budget = item_budget(total_budget, max(len(files), 1))
    return [file_payload(path, budget) for path in files]


def file_payload(path: Path, budget: int) -> dict[str, object]:
    """Return safe outline payload for one selected file."""

    context = file_reader.select_file_context(
        file_reader.FileRequest(path=path, outline=True, budget=budget)
    )
    return {
        "path": str(context.path),
        "mode": context.mode,
        "text": sanitize.sanitize_text(context.text),
        "untrusted": True,
        "refused": context.refused,
        "reason": context.reason,
        "original_chars": context.original_chars,
        "selected_chars": context.selected_chars,
        "omitted_chars": context.omitted_chars,
    }


def item_budget(total_budget: int, item_count: int) -> int:
    """Return per-item context budget for selected excerpts."""

    divisor = max(item_count * 3, 1)
    return min(MAX_CONTEXT_ITEM_BUDGET, max(MIN_CONTEXT_ITEM_BUDGET, total_budget // divisor))


def unique_names(values: Iterable[object]) -> tuple[str, ...]:
    """Return unique strings preserving input order."""

    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value)
        if text not in seen:
            seen.add(text)
            output.append(text)
    return tuple(output)
