"""Tests for generated Pyright project configuration."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import run_pyright
from scripts.guardrail_config import GuardrailConfig


def test_write_pyright_config_uses_guardrail_mode_and_roots(tmp_path: Path) -> None:
    config = GuardrailConfig(
        package_paths=("scripts", ".codex/hooks"),
        test_roots=("tests",),
        pyright_type_checking_mode="strict",
    )

    path = run_pyright.write_pyright_config(tmp_path, config)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["typeCheckingMode"] == "strict"
    assert payload["include"] == ["scripts", ".codex/hooks", "tests"]
