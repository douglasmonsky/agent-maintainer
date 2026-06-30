"""Tests for maintainer runtime environment policy."""

from __future__ import annotations

import sys

import pytest

from agent_maintainer.core import runtime as maintainer_runtime


def test_hardened_subprocess_env_disables_bytecode_writes_by_default() -> None:
    environment = maintainer_runtime.hardened_subprocess_env({})

    assert environment["PYTHONDONTWRITEBYTECODE"] == "1"


def test_hardened_subprocess_env_allows_explicit_bytecode_opt_in() -> None:
    environment = maintainer_runtime.hardened_subprocess_env(
        {
            "AGENT_MAINTAINER_WRITE_BYTECODE": "true",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )

    assert "PYTHONDONTWRITEBYTECODE" not in environment


def test_hardened_subprocess_env_allows_opt_in_without_existing_disable_flag() -> None:
    environment = maintainer_runtime.hardened_subprocess_env(
        {"AGENT_MAINTAINER_WRITE_BYTECODE": "true"}
    )

    assert environment == {"AGENT_MAINTAINER_WRITE_BYTECODE": "true"}


def test_disable_bytecode_writes_sets_current_process_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENT_MAINTAINER_WRITE_BYTECODE", raising=False)
    monkeypatch.setattr(sys, "dont_write_bytecode", False)

    maintainer_runtime.disable_bytecode_writes()

    assert sys.dont_write_bytecode is True
