"""Tests for the advisory TypeScript coverage CLI and renderers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_maintainer.cli import main as maintainer_main
from agent_maintainer.test_intel.typescript_coverage import (
    ADVISORY_NOTE,
    TypeScriptCoverageFileFact,
    TypeScriptCoverageReport,
)
from agent_maintainer.test_intel.typescript_coverage_reporting import (
    render_json,
    render_text,
)

EXPECTED_DETAIL_LIMIT = 50
FULL_COVERAGE_PERCENT = 100.0


def test_render_json_exposes_stable_advisory_contract() -> None:
    """JSON output contains exact aggregate and per-file facts."""

    payload = json.loads(render_json(sample_report()))

    assert payload == {
        "artifact_path": "coverage/lcov.info",
        "base_ref": "HEAD",
        "changed_line_coverage": 50.0,
        "changed_source": ["src/a.ts", "src/b.ts", "src/missing.ts"],
        "covered_changed_lines": 1,
        "executable_changed_lines": 2,
        "files": [
            {
                "changed_line_coverage": 50.0,
                "covered_changed_lines": 1,
                "executable_changed_lines": 2,
                "missed_changed_lines": 1,
                "path": "src/a.ts",
            },
            {
                "changed_line_coverage": None,
                "covered_changed_lines": 0,
                "executable_changed_lines": 0,
                "missed_changed_lines": 0,
                "path": "src/b.ts",
            },
        ],
        "matched_file_count": 2,
        "missed_changed_lines": 1,
        "missing_from_lcov": ["src/missing.ts"],
        "note": ADVISORY_NOTE,
        "source_root": ".",
        "staged": False,
    }


def test_render_text_bounds_file_and_missing_details() -> None:
    """Text output reserves its final detail line for an omission marker."""

    files = tuple(
        TypeScriptCoverageFileFact(
            path=f"src/file-{index:03d}.ts",
            executable_changed_lines=0,
            covered_changed_lines=0,
            missed_changed_lines=0,
            changed_line_coverage=None,
        )
        for index in range(EXPECTED_DETAIL_LIMIT)
    )
    report = TypeScriptCoverageReport(
        artifact_path="coverage/lcov.info",
        source_root=".",
        base_ref="HEAD",
        staged=False,
        changed_source=(*(fact.path for fact in files), "src/missing.ts"),
        missing_from_lcov=("src/missing.ts",),
        executable_changed_lines=0,
        covered_changed_lines=0,
        missed_changed_lines=0,
        changed_line_coverage=None,
        matched_file_count=len(files),
        files=files,
    )

    output = render_text(report)

    assert "changed-line coverage: unknown" in output
    assert "advisory" in output.lower()
    assert "2 detail line(s) omitted" in output
    detail_section = output.split("Details:\n", maxsplit=1)[1].split("\n\nNote:", maxsplit=1)[0]
    detail_lines = [line for line in detail_section.splitlines() if line.startswith("- ")]
    assert len(detail_lines) == EXPECTED_DETAIL_LIMIT


def test_render_text_counts_model_level_omissions() -> None:
    """The omission marker includes facts dropped before text rendering."""

    report = sample_report()
    report = TypeScriptCoverageReport(
        **{
            **report.__dict__,
            "matched_file_count": 102,
        }
    )

    output = render_text(report)

    assert "100 detail line(s) omitted" in output


def test_cli_reports_default_lcov_as_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Top-level CLI exposes the conventional artifact default."""

    create_repo(tmp_path)
    write_file(tmp_path, "src/app.ts", "old();\n")
    commit_all(tmp_path)
    write_file(tmp_path, "src/app.ts", "new();\n")
    write_file(
        tmp_path,
        "coverage/lcov.info",
        "SF:src/app.ts\nDA:1,1\nend_of_record\n",
    )
    monkeypatch.chdir(tmp_path)

    status = maintainer_main(
        ["test-intel", "typescript-coverage", "--format", "json"]
    )

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["artifact_path"] == "coverage/lcov.info"
    assert payload["changed_line_coverage"] == FULL_COVERAGE_PERCENT
    assert payload["note"] == ADVISORY_NOTE


def test_cli_accepts_explicit_workspace_source_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Workspace-relative LCOV records use an explicit source root."""

    create_repo(tmp_path)
    write_file(tmp_path, "packages/web/src/app.ts", "old();\n")
    commit_all(tmp_path)
    write_file(tmp_path, "packages/web/src/app.ts", "new();\n")
    write_file(
        tmp_path,
        "artifacts/web.lcov",
        "SF:src/app.ts\nDA:1,0\nend_of_record\n",
    )
    monkeypatch.chdir(tmp_path)

    status = maintainer_main(
        [
            "test-intel",
            "typescript-coverage",
            "--lcov",
            "artifacts/web.lcov",
            "--source-root",
            "packages/web",
        ]
    )

    output = capsys.readouterr().out
    assert status == 0
    assert "changed-line coverage: 0.00%" in output
    assert "packages/web/src/app.ts" in output


def test_cli_returns_error_for_missing_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Explicit command failure returns one concise stderr message."""

    create_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    status = maintainer_main(["test-intel", "typescript-coverage"])

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert "TypeScript coverage unavailable" in captured.err
    assert str(tmp_path) not in captured.err


def sample_report() -> TypeScriptCoverageReport:
    """Return a stable renderer fixture."""

    files = (
        TypeScriptCoverageFileFact("src/a.ts", 2, 1, 1, 50.0),
        TypeScriptCoverageFileFact("src/b.ts", 0, 0, 0, None),
    )
    return TypeScriptCoverageReport(
        artifact_path="coverage/lcov.info",
        source_root=".",
        base_ref="HEAD",
        staged=False,
        changed_source=("src/a.ts", "src/b.ts", "src/missing.ts"),
        missing_from_lcov=("src/missing.ts",),
        executable_changed_lines=2,
        covered_changed_lines=1,
        missed_changed_lines=1,
        changed_line_coverage=50.0,
        matched_file_count=2,
        files=files,
    )


def create_repo(path: Path) -> None:
    """Initialize a temporary Git repository."""

    run_git(path, "init")
    run_git(path, "config", "user.email", "agent-maintainer@example.invalid")
    run_git(path, "config", "user.name", "Agent Maintainer Test")


def write_file(root: Path, relative: str, content: str) -> None:
    """Write one fixture file."""

    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def commit_all(path: Path) -> None:
    """Commit all fixture files."""

    run_git(path, "add", "--", ".")
    run_git(path, "commit", "-m", "initial")


def run_git(path: Path, *args: str) -> None:
    """Run Git in a temporary repository."""

    subprocess.run(
        ["git", *args],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
