"""Tests context budget helpers."""

from __future__ import annotations

import pytest

from agent_context.budget import bound_single_item_text, bound_text
from agent_context.models import ContextBudget
from agent_maintainer.context import budget as old_budget
from agent_maintainer.context import models as old_models

TRUNCATION_ORIGINAL_LINES = 3
LINE_LIMIT_ORIGINAL_LINES = 4
LINE_LIMIT_OMITTED_LINES = 2
SINGLE_ITEM_CHAR_LIMIT = 3


def test_old_context_budget_imports_delegate_to_agent_context() -> None:
    """Old context budget imports remain compatibility shims."""
    assert old_budget.bound_text is bound_text
    assert old_models.ContextBudget is ContextBudget


def test_bound_text_tracks_char_and_line_omissions() -> None:
    """Text truncation reports original and omitted sizes."""

    bounded = bound_text("alpha\nbravo\ncharlie\n", ContextBudget(max_chars=11, max_items=5))

    assert bounded.text == "alpha\nbravo"
    assert bounded.original_chars == len("alpha\nbravo\ncharlie\n")
    assert bounded.original_lines == TRUNCATION_ORIGINAL_LINES
    assert bounded.truncated is True
    assert bounded.omitted_chars == len("\ncharlie\n")
    assert bounded.omitted_lines == 1


def test_bound_text_respects_line_limit_before_char_limit() -> None:
    """Line limits apply before character limits."""

    bounded = bound_text(
        "one\ntwo\nthree\nfour\n",
        ContextBudget(max_chars=100, max_items=5, max_lines=2),
    )

    assert bounded.text == "one\ntwo\n"
    assert bounded.original_lines == LINE_LIMIT_ORIGINAL_LINES
    assert bounded.omitted_lines == LINE_LIMIT_OMITTED_LINES
    assert bounded.truncated is True


def test_bound_single_item_text_caps_chars() -> None:
    """Single-item helper uses character budget."""

    bounded = bound_single_item_text("abcdef", SINGLE_ITEM_CHAR_LIMIT)

    assert bounded.text == "abc"
    assert bounded.omitted_chars == SINGLE_ITEM_CHAR_LIMIT
    assert bounded.truncated is True


@pytest.mark.parametrize(
    "budget",
    (
        ContextBudget(max_chars=0, max_items=1),
        ContextBudget(max_chars=10, max_items=0),
    ),
)
def test_zero_budget_values_are_allowed(budget: ContextBudget) -> None:
    """Zero budgets are valid limits."""

    assert budget.max_chars >= 0
    assert budget.max_items >= 0


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"max_chars": -1, "max_items": 1}, "max_chars"),
        ({"max_chars": 1, "max_items": -1}, "max_items"),
        ({"max_chars": 1, "max_items": 1, "max_lines": -1}, "max_lines"),
    ),
)
def test_negative_budget_values_are_rejected(kwargs: dict[str, int], message: str) -> None:
    """Negative budget values are rejected early."""

    with pytest.raises(ValueError, match=message):
        ContextBudget(**kwargs)
