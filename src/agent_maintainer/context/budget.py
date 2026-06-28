"""Budget helpers for bounded context output."""

from __future__ import annotations

from agent_maintainer.context.models import BoundedText, ContextBudget


def bound_text(text: str, budget: ContextBudget) -> BoundedText:
    """Return text capped by character and optional line limits."""

    original_chars = len(text)
    original_lines = count_lines(text)
    bounded = apply_line_limit(text, budget.max_lines)
    if len(bounded) > budget.max_chars:
        bounded = bounded[: budget.max_chars]
    bounded_lines = count_lines(bounded)
    omitted_chars = original_chars - len(bounded)
    omitted_lines = max(0, original_lines - bounded_lines)
    return BoundedText(
        text=bounded,
        original_chars=original_chars,
        original_lines=original_lines,
        truncated=omitted_chars > 0 or omitted_lines > 0,
        omitted_chars=omitted_chars,
        omitted_lines=omitted_lines,
    )


def apply_line_limit(text: str, max_lines: int | None) -> str:
    """Return at most max_lines from text while preserving line endings."""

    if max_lines is None:
        return text
    return "".join(text.splitlines(keepends=True)[:max_lines])


def count_lines(text: str) -> int:
    """Count display lines in a text block."""

    if not text:
        return 0
    return len(text.splitlines())
