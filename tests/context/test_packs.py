"""Tests bounded repair context packs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from agent_context.pack_rendering import (
    command_pointer_lines,
    exact_fact_lines,
    fact_location,
    fact_pointer_lines,
    fact_summary,
    omitted_count_lines,
    ratchet_lines,
    render_pack_pointer,
    supporting_context_lines,
    supporting_item_lines,
    top_target_lines,
)
from agent_maintainer.context import cli as context_cli
from agent_maintainer.context.pack import cli as pack_cli
from agent_maintainer.context.pack import rendering as compatibility_rendering
from agent_maintainer.context.pack.builder import (
    ContextPackRequest,
    build_context_pack,
    payload_expansion_commands,
    payload_omitted_counts,
    selected_log_names,
    write_context_pack,
)
from agent_maintainer.context.pack.ratchet import target_commands

PACK_BUDGET = 2_200


def test_context_pack_rendering_compatibility_shim() -> None:
    """Old product import path forwards to reusable rendering helpers."""

    assert compatibility_rendering.render_pack_pointer is render_pack_pointer


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


def test_context_pack_writer_rejects_symlinked_output_directory(tmp_path: Path) -> None:
    """A direct pack write cannot redirect artifacts through a symlink parent."""

    log_dir = tmp_path / ".verify-logs"
    outside = tmp_path / "outside"
    log_dir.mkdir()
    outside.mkdir()
    canary = outside / "PACK.md"
    canary.write_text("unchanged\n", encoding="utf-8")
    (log_dir / "context").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="real directory"):
        write_context_pack(ContextPackRequest(log_dir=log_dir))

    assert canary.read_text(encoding="utf-8") == "unchanged\n"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO support is POSIX-only")
def test_context_pack_preflights_both_outputs_before_first_write(tmp_path: Path) -> None:
    """An unsafe JSON target leaves the earlier Markdown target untouched."""

    log_dir = tmp_path / ".verify-logs"
    context_dir = log_dir / "context"
    context_dir.mkdir(parents=True)
    markdown = context_dir / "PACK.md"
    markdown.write_text("unchanged\n", encoding="utf-8")
    os.mkfifo(context_dir / "PACK.json")

    with pytest.raises(ValueError, match="regular file"):
        write_context_pack(ContextPackRequest(log_dir=log_dir))

    assert markdown.read_text(encoding="utf-8") == "unchanged\n"


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


def test_context_pack_refuses_file_outside_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit pack file paths cannot escape the process workspace root."""

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.py"
    secret = "PACK-OUTSIDE-CANARY"
    outside.write_text(secret, encoding="utf-8")
    monkeypatch.chdir(workspace)

    pack = build_context_pack(
        ContextPackRequest(
            log_dir=Path(".verify-logs"),
            files=(Path("../outside.py"),),
        ),
    )

    selected = cast(list[dict[str, object]], pack.payload["selected_file_outlines"])
    assert selected[0]["refused"] is True
    assert selected[0]["reason"] == "path escapes workspace root"
    assert secret not in str(selected[0])


def test_context_pack_refuses_manifest_outside_log_and_artifact_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Manifest metadata cannot redirect pack readers outside the workspace."""

    workspace = tmp_path / "workspace"
    log_dir = workspace / ".verify-logs"
    outside_log = tmp_path / "outside.log"
    outside_artifact = tmp_path / "outside.json"
    log_secret = "OUTSIDE-LOG-CANARY"
    artifact_secret = "OUTSIDE-ARTIFACT-CANARY"
    outside_log.write_text(log_secret, encoding="utf-8")
    outside_artifact.write_text(artifact_secret, encoding="utf-8")
    log_dir.mkdir(parents=True)
    (log_dir / "manifest.json").write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "name": "ruff",
                        "status": "failed",
                        "exit_code": 1,
                        "log_path": str(outside_log),
                        "log_bytes": outside_log.stat().st_size,
                        "artifacts": [str(outside_artifact)],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(workspace)

    pack = build_context_pack(ContextPackRequest(log_dir=Path(".verify-logs")))

    rendered = json.dumps(pack.payload)
    assert log_secret not in rendered
    assert artifact_secret not in rendered
    selected_logs = cast(list[dict[str, object]], pack.payload["selected_logs"])
    assert selected_logs[0]["refused"] is True
    assert "workspace-relative" in str(selected_logs[0]["text"])


def test_context_pack_checks_the_exact_manifest_artifact_before_parsing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A safe basename fallback cannot mask a symlinked manifest artifact."""

    workspace = tmp_path / "workspace"
    log_dir = workspace / ".verify-logs"
    outside_dir = tmp_path / "outside"
    other_cwd = tmp_path / "other"
    log_dir.mkdir(parents=True)
    outside_dir.mkdir()
    other_cwd.mkdir()
    (workspace / "linked").symlink_to(outside_dir, target_is_directory=True)
    outside_secret = "SYMLINKED-ARTIFACT-CANARY"
    (outside_dir / "ruff.json").write_text(
        json.dumps(
            [
                {
                    "filename": "src/escaped.py",
                    "location": {"row": 1, "column": 1},
                    "code": "F401",
                    "message": outside_secret,
                }
            ]
        ),
        encoding="utf-8",
    )
    (log_dir / "ruff.json").write_text("[]\n", encoding="utf-8")
    (log_dir / "ruff.log").write_text("ruff failed\n", encoding="utf-8")
    (log_dir / "manifest.json").write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "name": "ruff",
                        "status": "failed",
                        "exit_code": 1,
                        "log_path": ".verify-logs/ruff.log",
                        "artifacts": ["linked/ruff.json"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(other_cwd)

    pack = build_context_pack(ContextPackRequest(log_dir=log_dir))

    assert outside_secret not in json.dumps(pack.payload)
    facts = cast(list[dict[str, object]], pack.payload["exact_repair_facts"])
    assert facts[0]["path"] is None


def test_context_pack_cli_outputs_json_and_writes_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Context pack CLI prints JSON while writing both artifacts."""

    log_dir = tmp_path / ".verify-logs"
    write_log(log_dir, "ruff", "ruff failed\n")
    monkeypatch.setattr(
        pack_cli,
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


# docsync:evidence.start evidence.context_safety.pointer_first_pack_tests
def test_context_pack_cli_outputs_pointer_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Context pack CLI writes full artifacts but prints compact pointer."""

    log_dir = tmp_path / ".verify-logs"
    write_manifest(log_dir, "ruff")
    write_log(log_dir, "ruff", "ruff failed\n")
    monkeypatch.setattr(
        pack_cli,
        "load_config",
        lambda: SimpleNamespace(
            context_pack_budget_chars=5_000,
            ratchet_baseline_path=str(tmp_path / "missing.json"),
            context_max_failure_items=5,
            ratchet_target_limit=3,
        ),
    )

    result = context_cli.main(["--log-dir", str(log_dir), "pack", "--check", "ruff"])

    output = capsys.readouterr().out
    assert result == 0
    assert output.startswith("Result: FAIL\nProfile: agent-hook\nRun ID: unavailable")
    assert "Top repair facts:" in output
    assert "Likely next action:" in output
    assert "Expand only if needed:" in output
    assert "Context pack artifact:" in output
    assert "# Agent Maintainer Context Pack" not in output
    assert "Read:" not in output
    assert (log_dir / "context" / "PACK.md").exists()


def test_context_pack_cli_prints_full_markdown_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Context pack CLI prints full Markdown only behind explicit flag."""

    log_dir = tmp_path / ".verify-logs"
    write_manifest(log_dir, "ruff")
    write_log(log_dir, "ruff", "ruff failed\n")
    monkeypatch.setattr(
        pack_cli,
        "load_config",
        lambda: SimpleNamespace(
            context_pack_budget_chars=5_000,
            ratchet_baseline_path=str(tmp_path / "missing.json"),
            context_max_failure_items=5,
            ratchet_target_limit=3,
        ),
    )

    result = context_cli.main(
        ["--log-dir", str(log_dir), "pack", "--check", "ruff", "--print-full"]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert output.startswith("# Agent Maintainer Context Pack")
    assert "## Exact Repair Facts" in output


# docsync:evidence.end evidence.context_safety.pointer_first_pack_tests


def test_context_pack_helpers_handle_defensive_branches() -> None:
    """Pack helpers handle malformed optional payload slices."""
    pointer = render_pack_pointer(
        {"exact_repair_facts": [], "expansion_commands": []},
        display_path=".verify-logs/context/PACK.md",
    )

    assert "Likely next action:\nInspect the first failed check summary." in pointer
    assert selected_log_names(ContextPackRequest(), ()) == ()
    assert target_commands({"top_targets": "invalid"}) == ()
    assert target_commands({"top_targets": [None, {"first_command": "inspect"}]}) == ("inspect",)
    assert payload_expansion_commands({"expansion_commands": [None, "inspect"]}) == [
        "None",
        "inspect",
    ]
    assert payload_omitted_counts({"omitted_counts": {"logs": 2, "bad": "value"}}) == {
        "logs": 2,
    }
    assert fact_pointer_lines("invalid", 1) == []
    assert command_pointer_lines("invalid", 1) == []
    assert command_pointer_lines([], 1) == [
        "python -m agent_maintainer context failures --limit 20"
    ]
    assert fact_location("src/example.py", None) == "src/example.py "
    assert (
        fact_summary(
            {"check": "pyright", "path": "src/example.py", "line": 2, "message": "bad"},
        )
        == "pyright: src/example.py:2 bad"
    )
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
                "log_path": str(Path(log_dir.name) / f"{check_name}.log"),
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
