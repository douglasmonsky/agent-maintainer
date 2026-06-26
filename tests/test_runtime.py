"""Tests for guardrail runtime environment policy."""

from __future__ import annotations

import sys

import pytest

from scripts.guardrail_core import runtime as guardrail_runtime


def test_hardened_subprocess_env_disables_bytecode_writes_by_default() -> None:
    environment = guardrail_runtime.hardened_subprocess_env({})

    assert environment["PYTHONDONTWRITEBYTECODE"] == "1"


def test_hardened_subprocess_env_allows_explicit_bytecode_opt_in() -> None:
    environment = guardrail_runtime.hardened_subprocess_env(
        {
            "AI_GUARDRAILS_WRITE_BYTECODE": "true",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )

    assert "PYTHONDONTWRITEBYTECODE" not in environment


def test_disable_bytecode_writes_sets_current_process_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_GUARDRAILS_WRITE_BYTECODE", raising=False)
    monkeypatch.setattr(sys, "dont_write_bytecode", False)

    guardrail_runtime.disable_bytecode_writes()

    assert sys.dont_write_bytecode is True
