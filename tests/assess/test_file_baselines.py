"""Tests provider-neutral file baseline assessment."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
from pathlib import Path

import pytest

from agent_maintainer.assess import cli, reporting
from agent_maintainer.assess.file_baselines import build_file_baseline_report
from agent_maintainer.assess.models import (
    FileBaselineFinding,
    FileBaselineGroupSummary,
    FileBaselineReport,
)
from agent_maintainer.config import loader
from agent_maintainer.config.schema import FileBaselineGroupConfig, MaintainerConfig

DOCS_CONFIG_FILE_COUNT = 3
DOCS_GROUP = "docs"
DOCS_GLOB = "docs/**/*.md"
DOCS_GUIDE = "docs/guide.md"
MAX_PHYSICAL_LINES = 500
MAX_NONBLANK_LINES = 375
CHANGE_LINE_WARN = 400
GENERATED_FILE_LINES = 20
TEXT_CHANGED_LINES = 30


def test_config_loads_nested_baselines(tmp_path: Path) -> None:
    """Nested file baseline config resolves into typed group config."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.agent_maintainer.file_baselines]
enabled = true
mode = "advisory"

[tool.agent_maintainer.file_baselines.groups.typescript_source]
include = ["src/**/*.{ts,tsx}"]
exclude = ["**/*.test.*", "**/__generated__/**"]
role = "source"
max_physical_lines = 500
max_nonblank_lines = 375
changed_file_warn = 8
changed_line_warn = 400
""".strip(),
        encoding="utf-8",
    )

    config = loader.apply_pyproject(
        MaintainerConfig(),
        loader.read_pyproject(pyproject),
    )

    assert config.file_baselines_enabled is True
    assert config.file_baselines_mode == "advisory"
    assert config.file_baselines == (
        FileBaselineGroupConfig(
            name="typescript_source",
            include=("src/**/*.{ts,tsx}",),
            exclude=("**/*.test.*", "**/__generated__/**"),
            role="source",
            max_physical_lines=MAX_PHYSICAL_LINES,
            max_nonblank_lines=MAX_NONBLANK_LINES,
            changed_file_warn=8,
            changed_line_warn=CHANGE_LINE_WARN,
        ),
    )


# docsync:evidence.start evidence.file_baselines.provider_neutral
def test_report_flags_generic_groups(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generic baseline groups count TSX/docs/config files without Python policy."""
    repo = _repo_with_baseline(tmp_path)
    _write(repo / "src/App.tsx", "export function App() {\n  return <main>Ready</main>;\n}\n")
    _write(repo / "src/__generated__/client.tsx", "x\n" * GENERATED_FILE_LINES)
    _write(repo / DOCS_GUIDE, "# Guide\n\nUse the app.\n")
    _write(repo / "settings/tool.toml", "[tool.example]\n")
    _write(repo / "settings/lint.yaml", "rules: {}\n")

    config = MaintainerConfig(
        file_baselines_enabled=True,
        file_baselines=(
            FileBaselineGroupConfig(
                name="typescript",
                include=("src/**/*.{ts,tsx}",),
                exclude=("**/__generated__/**",),
                role="source",
                max_physical_lines=2,
                max_nonblank_lines=2,
                changed_file_warn=1,
                changed_line_warn=2,
            ),
            FileBaselineGroupConfig(
                name="docs-config",
                include=(DOCS_GLOB, "settings/*.{toml,yaml}"),
                role="docs-config",
                max_physical_lines=10,
            ),
        ),
    )

    monkeypatch.chdir(repo)
    report = build_file_baseline_report(
        repo,
        config,
        base_ref="HEAD",
        staged=False,
    )

    by_group = {group.name: group for group in report.groups}
    assert (
        by_group["typescript"].matched_files,
        by_group["typescript"].changed_files,
        by_group["typescript"].changed_lines > 0,
        by_group["docs-config"].matched_files,
    ) == (1, 1, True, DOCS_CONFIG_FILE_COUNT)
    assert {finding.kind for finding in report.findings} == {
        "changed-lines",
        "nonblank-lines",
        "physical-lines",
    }
    assert all("__generated__" not in finding.path for finding in report.findings)


def test_cli_renders_baseline_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI reads configured file groups and emits compact JSON."""
    repo = _repo_with_baseline(tmp_path)
    _write(
        repo / "pyproject.toml",
        f"""
[tool.agent_maintainer.file_baselines]
enabled = true

[tool.agent_maintainer.file_baselines.groups.docs]
include = ["{DOCS_GLOB}"]
max_physical_lines = 1
""".strip(),
    )
    _write(repo / DOCS_GUIDE, "# Guide\n\nMore detail.\n")

    status = cli.main(
        [
            "file-baselines",
            "--target",
            str(repo),
            "--base-ref",
            "HEAD",
            "--json",
        ],
    )

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["enabled"] is True
    assert payload["groups"][0]["name"] == DOCS_GROUP
    assert payload["findings"][0]["kind"] == "physical-lines"


# docsync:evidence.end evidence.file_baselines.provider_neutral


def test_text_renders_findings() -> None:
    """Text renderer shows empty states and detailed finding lines."""
    empty_text = reporting.render_file_baselines_text(
        FileBaselineReport(
            target="/repo",
            enabled=True,
            mode="advisory",
            groups=(),
            findings=(),
            next_commands=("python -m agent_maintainer assess file-baselines",),
        ),
    )

    assert "Groups:\n- None" in empty_text
    assert "Findings:\n- None" in empty_text

    finding_text = reporting.render_file_baselines_text(
        FileBaselineReport(
            target="/repo",
            enabled=True,
            mode="advisory",
            groups=(
                FileBaselineGroupSummary(
                    name=DOCS_GROUP,
                    role=DOCS_GROUP,
                    matched_files=2,
                    changed_files=1,
                    changed_lines=TEXT_CHANGED_LINES,
                    findings=1,
                ),
            ),
            findings=(
                FileBaselineFinding(
                    group=DOCS_GROUP,
                    path=DOCS_GUIDE,
                    kind="physical-lines",
                    message="701 physical lines exceeds 700",
                    recommendation="Split the file by topic.",
                ),
            ),
            next_commands=("python -m agent_maintainer assess file-baselines --json",),
        ),
    )

    assert "- docs (docs): matched=2, changed=1 files/30 lines, findings=1" in finding_text
    assert "docs/physical-lines: docs/guide.md: 701 physical lines exceeds 700" in finding_text
    assert "Split the file by topic." in finding_text


def test_invalid_nested_group_errors(tmp_path: Path) -> None:
    """Nested group config rejects missing include patterns."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.agent_maintainer.file_baselines]
enabled = true

[tool.agent_maintainer.file_baselines.groups.empty]
role = "docs"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="include"):
        loader.apply_pyproject(MaintainerConfig(), loader.read_pyproject(pyproject))

    config = loader.apply_pyproject(
        MaintainerConfig(),
        {
            "file_baselines": {
                "enabled": True,
                "mode": "blocking",
                "groups": {DOCS_GROUP: {"include": [DOCS_GLOB]}},
            },
        },
    )
    assert config.file_baselines_mode == "blocking"
    assert config.file_baselines[0].name == DOCS_GROUP


def _repo_with_baseline(tmp_path: Path) -> Path:
    """Create a Git repo with a committed baseline."""
    if shutil.which("git") is None:
        pytest.skip("git executable required")
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "src/App.tsx", "export function App() { return null; }\n")
    _write(repo / DOCS_GUIDE, "# Guide\n")
    _write(repo / "settings/tool.toml", "[tool.example]\n")
    _write(repo / "settings/lint.yaml", "rules: {}\n")
    _git(repo, "init")
    _git(repo, "config", "user.name", "Agent Maintainer Test")
    _git(repo, "config", "user.email", "agent-maintainer@example.test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    return repo


def _write(path: Path, content: str) -> None:
    """Write fixture content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _git(repo: Path, *args: str) -> None:
    """Run Git command in fixture repository."""
    subprocess.run(  # nosec B603
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
