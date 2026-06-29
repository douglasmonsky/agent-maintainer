"""Tests bounded repair context packs."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from agent_maintainer.context import cli as context_cli
from agent_maintainer.context.pack_rendering import (
    exact_fact_lines,
    omitted_count_lines,
    ratchet_lines,
    supporting_context_lines,
    supporting_item_lines,
    top_target_lines,
)
from agent_maintainer.context.packs import (
    ContextPackRequest,
    build_context_pack,
    selected_log_names,
    target_commands,
    write_context_pack,
)

PACK_BUDGET = 2_200


def test_context_pack_writes_markdown_and_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Context pack writes expected artifacts and required sections."""

    monkeypatch.chdir(tmp_path)
    log_dir = tmp_path / ".verify-logs"
    write_manifest(log_dir, "pytest-coverage")
    write_log(log_dir, "pytest-coverage", "TOKEN=super-secret\ncoverage failed\n")
    source_file = write_source_file(tmp_path)

    pack = write_context_pack(
        ContextPackRequest(
            log_dir=log_dir,
            budget=8_000,
            files=(source_file.relative_to(tmp_path),),
            baseline_path=tmp_path / ".agent-maintainer" / "missing.json",
        ),
    )

    payload = json.loads(pack.json_path.read_text(encoding="utf-8"))
    markdown = pack.markdown_path.read_text(encoding="utf-8")
    assert pack.markdown_path.exists()
    assert pack.json_path.exists()
    assert markdown.index("## Exact Repair Facts") < markdown.index("## Supporting Context")
    for heading in (
        "## Untrusted Content Labels",
        "## Ratchet State",
        "## Top Targets",
        "## Selected File Outlines",
        "## Selected Logs",
        "## Omitted Counts",
        "## Expansion Commands",
    ):
        assert heading in markdown
    assert "TOKEN=[REDACTED]" in markdown
    assert payload["exact_repair_facts"][0]["check"] == "pytest-coverage"
    assert payload["selected_logs"][0]["untrusted"] is True
    assert payload["outputs"]["markdown"].endswith(".verify-logs/context/PACK.md")


def test_context_pack_markdown_is_bounded(tmp_path: Path) -> None:
    """Context pack honors requested Markdown budget."""

    log_dir = tmp_path / ".verify-logs"
    write_manifest(log_dir, "ruff")
    write_log(log_dir, "ruff", "\n".join(f"line {index}" for index in range(500)))

    pack = build_context_pack(
        ContextPackRequest(
            log_dir=log_dir,
            budget=PACK_BUDGET,
            baseline_path=tmp_path / "missing-baseline.json",
        ),
    )

    assert len(pack.markdown) <= PACK_BUDGET
    omitted_counts = cast(dict[str, int], pack.payload["omitted_counts"])
    assert omitted_counts["pack_markdown_omitted_chars"] > 0
    assert "## Omitted Counts" in pack.markdown
    assert "## Expansion Commands" in pack.markdown


def test_context_pack_cli_outputs_json_and_writes_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Context pack CLI prints JSON while writing both artifacts."""

    log_dir = tmp_path / ".verify-logs"
    write_log(log_dir, "ruff", "ruff failed\n")
    monkeypatch.setattr(
        context_cli,
        "load_config",
        lambda: SimpleNamespace(
            context_pack_budget_chars=5_000,
            ratchet_baseline_path=str(tmp_path / "missing.json"),
            context_max_failure_items=5,
            ratchet_target_limit=3,
        ),
    )

    result = context_cli.main(
        ["--log-dir", str(log_dir), "pack", "--check", "ruff", "--format", "json"],
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["selected_logs"][0]["check"] == "ruff"
    assert (log_dir / "context" / "PACK.md").exists()
    assert (log_dir / "context" / "PACK.json").exists()


def test_context_pack_helpers_handle_defensive_branches() -> None:
    """Pack helpers handle malformed optional payload slices."""

    assert selected_log_names(ContextPackRequest(), ()) == ()
    assert target_commands({"top_targets": "invalid"}) == ()
    assert exact_fact_lines([object()]) == ["- Unknown failure fact."]
    assert supporting_context_lines(object()) == ["- No supporting context selected."]
    assert "- Stale reasons:" in ratchet_lines(
        {"available": True, "baseline_path": "base.json", "counts": {}, "stale_reasons": ["old"]},
    )
    assert top_target_lines([object()]) == ["- Unknown target."]
    assert supporting_item_lines([object()], "path", "empty") == ["- Unknown supporting item."]
    assert omitted_count_lines(object()) == []


def write_manifest(log_dir: Path, check_name: str) -> None:
    """Write verifier manifest fixture."""

    log_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "checks": [
            {
                "name": check_name,
                "status": "failed",
                "exit_code": 1,
                "log_path": str(log_dir / f"{check_name}.log"),
            },
        ],
    }
    (log_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def write_log(log_dir: Path, check_name: str, text: str) -> None:
    """Write verifier log fixture."""

    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{check_name}.log").write_text(text, encoding="utf-8")


def write_source_file(repo: Path) -> Path:
    """Write source file for outline fixture."""

    source = repo / "src" / "pkg" / "app.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        '"""Example module."""\n\n'
        "class Example:\n"
        '    """Example class."""\n\n'
        "    def method(self) -> int:\n"
        "        return 1\n",
        encoding="utf-8",
    )
    return source
