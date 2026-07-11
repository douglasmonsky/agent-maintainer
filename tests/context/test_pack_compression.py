"""Tests context pack compression behavior."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from agent_context.compression import headroom as headroom_backend
from agent_maintainer.context import cli as context_cli
from agent_maintainer.context.pack import cli as pack_cli
from agent_maintainer.context.pack.builder import ContextPackRequest, build_context_pack
from agent_maintainer.context.pack.compression import (
    PackCompressionRequest,
    compress_supporting_context,
    headroom_fallback_message,
)
from tests.support.callbacks import constant_callback


def test_context_pack_compresses_supporting_context_not_exact_facts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Headroom compression only receives selected supporting context."""

    log_dir = write_failure_log(tmp_path, "ruff", "line one\nline two\n")
    received: list[list[dict[str, str]]] = []

    def compress_messages(messages: list[dict[str, str]]) -> str:
        received.append(messages)
        return "compressed support"

    fake_module = SimpleNamespace(compress=compress_messages)
    monkeypatch.setattr(
        headroom_backend.importlib,
        "import_module",
        constant_callback(fake_module),
    )

    pack = build_context_pack(
        ContextPackRequest(
            log_dir=log_dir,
            check="ruff",
            compression_backend="headroom",
            compression_target_chars=20,
        )
    )

    exact_facts = cast(list[dict[str, object]], pack.payload["exact_repair_facts"])
    selected_logs = cast(list[dict[str, object]], pack.payload["selected_logs"])
    compression = cast(dict[str, object], selected_logs[0]["compression"])

    assert exact_facts[0]["message"] == "ruff failed with exit code 1"
    assert selected_logs[0]["text"] == "compressed support"
    assert compression["backend"] == "headroom"
    assert received == [[{"role": "user", "content": "line one\nline two"}]]


def test_context_pack_headroom_failure_falls_back_when_optional(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Optional Headroom failures fall back to deterministic extraction."""

    log_dir = write_failure_log(tmp_path, "ruff", "line one\nline two\n")

    def fail_compress(_content: str) -> str:
        raise RuntimeError("provider failed")

    fake_module = SimpleNamespace(compress=fail_compress)
    monkeypatch.setattr(
        headroom_backend.importlib,
        "import_module",
        constant_callback(fake_module),
    )
    monkeypatch.chdir(tmp_path)

    result = context_cli.main(
        ["--log-dir", str(log_dir), "pack", "--check", "ruff", "--compress", "headroom"]
    )

    assert result == 0
    assert (
        "WARN: Headroom compression failed; using deterministic extractive context."
        in capsys.readouterr().err
    )


def test_context_pack_headroom_missing_required_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Required Headroom compression fails when dependency is unavailable."""

    log_dir = write_failure_log(tmp_path, "ruff", "line one\n")

    def missing_module(_name: str) -> object:
        raise ImportError("missing")

    monkeypatch.setattr(headroom_backend.importlib, "import_module", missing_module)
    monkeypatch.chdir(tmp_path)

    result = context_cli.main(
        [
            "--log-dir",
            str(log_dir),
            "pack",
            "--check",
            "ruff",
            "--compress",
            "headroom",
            "--require-compression",
        ]
    )

    assert result == 1
    assert "agent-maintainer[compression]" in capsys.readouterr().err


def test_context_pack_json_reports_compression_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Context pack JSON includes compression metadata."""

    log_dir = write_failure_log(tmp_path, "ruff", "alpha beta gamma\n")
    monkeypatch.chdir(tmp_path)

    result = context_cli.main(
        [
            "--log-dir",
            str(log_dir),
            "pack",
            "--check",
            "ruff",
            "--compress",
            "truncate",
            "--format",
            "json",
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["compression"]["enabled"] is True
    assert payload["compression"]["backend"] == "truncate"


def test_context_pack_uses_configured_compression_backend(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Context pack CLI can read compression backend from config."""

    log_dir = write_failure_log(tmp_path, "ruff", "alpha beta gamma\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        pack_cli,
        "load_config",
        lambda: SimpleNamespace(
            context_compression_backend="truncate",
            context_compression_enabled=True,
            context_compression_require_backend=False,
            context_compression_target_ratio=0.5,
            context_max_failure_items=5,
            context_pack_budget_chars=1_000,
            ratchet_baseline_path=str(tmp_path / "missing.json"),
            ratchet_target_limit=3,
        ),
    )

    result = context_cli.main(
        [
            "--log-dir",
            str(log_dir),
            "pack",
            "--check",
            "ruff",
            "--format",
            "json",
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["compression"]["backend"] == "truncate"


def test_pack_compression_skips_empty_items_and_defaults_target() -> None:
    """Pack compression preserves empty items and derives item target size."""

    result = compress_supporting_context(
        logs=[{"text": ""}, {"text": "alpha"}],
        files=[],
        request=PackCompressionRequest(backend="truncate"),
    )

    assert "compression" not in result.logs[0]
    assert result.logs[1]["text"] == "alpha"
    compression = cast(dict[str, object], result.logs[1]["compression"])
    assert compression["backend"] == "truncate"


def test_non_headroom_fallback_warning_names_backend() -> None:
    """Fallback warning names non-Headroom provider backends."""

    assert headroom_fallback_message("custom") == (
        "custom compression failed; using deterministic extractive context."
    )


def write_failure_log(root: Path, check_name: str, content: str) -> Path:
    """Write verifier manifest and log fixture."""

    log_dir = root / ".verify-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{check_name}.log"
    manifest = {
        "checks": [
            {
                "name": check_name,
                "status": "failed",
                "exit_code": 1,
                "log_path": str(Path(log_dir.name) / log_path.name),
            },
        ],
    }
    (log_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    log_path.write_text(content, encoding="utf-8")
    return log_dir
