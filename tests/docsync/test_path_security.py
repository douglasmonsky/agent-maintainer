"""Security tests for DocSync repository path and I/O boundaries."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from docsync import cli as docsync_cli
from docsync.config.defaults import DEFAULT_CONFIG_TEXT
from docsync.config.load import ConfigError, load_config
from docsync.config.paths import PathBoundaryError


@pytest.mark.parametrize(
    "output_key",
    ("index_json", "report_json", "review_packet_json", "review_prompt_md"),
)
@pytest.mark.parametrize("escaped", ("../../outside.txt", "/tmp/docsync-outside.txt"))
def test_config_rejects_every_escaped_output(
    tmp_path: Path,
    output_key: str,
    escaped: str,
) -> None:
    """Every repository-controlled output remains under the generated root."""
    repo_root = tmp_path / "repo"
    _write_config(repo_root, outputs={output_key: escaped})

    with pytest.raises(ConfigError, match=r"relative|\.\.|approved root"):
        load_config(repo_root)

    assert not (tmp_path / "outside.txt").exists()


def test_config_rejects_source_tree_as_output_root(tmp_path: Path) -> None:
    """A contained path cannot turn repository source into generated output."""
    repo_root = tmp_path / "repo"
    _write_config(
        repo_root,
        outputs={"directory": ".", "report_json": "pyproject.toml"},
    )

    with pytest.raises(ConfigError, match="output directory must remain under"):
        load_config(repo_root)


@pytest.mark.parametrize(
    "output_key",
    ("index_json", "report_json", "review_packet_json", "review_prompt_md"),
)
def test_config_rejects_output_file_equal_to_output_directory(
    tmp_path: Path,
    output_key: str,
) -> None:
    """A configured file cannot replace and poison its own output directory."""

    repo_root = tmp_path / "repo"
    _write_config(repo_root, outputs={output_key: ".docsync/out"})

    with pytest.raises(ConfigError, match="must be a file below"):
        load_config(repo_root)


def test_config_rejects_colliding_multi_file_outputs(tmp_path: Path) -> None:
    """Prompt JSON and Markdown destinations cannot overwrite one another."""

    repo_root = tmp_path / "repo"
    collision = ".docsync/out/review-output.txt"
    _write_config(
        repo_root,
        outputs={
            "review_packet_json": collision,
            "review_prompt_md": collision,
        },
    )

    with pytest.raises(ConfigError, match="output files must be distinct"):
        load_config(repo_root)


def test_config_rejects_collision_with_derived_sarif_output(tmp_path: Path) -> None:
    """A configured output cannot collide with the report's derived SARIF path."""

    repo_root = tmp_path / "repo"
    _write_config(
        repo_root,
        outputs={"index_json": ".docsync/out/report.sarif.json"},
    )

    with pytest.raises(ConfigError, match="output files must be distinct"):
        load_config(repo_root)


def test_config_rejects_collision_with_default_freshness_output(tmp_path: Path) -> None:
    """A configured artifact cannot overwrite passive freshness metadata."""

    repo_root = tmp_path / "repo"
    _write_config(
        repo_root,
        outputs={"index_json": ".docsync/out/freshness.json"},
    )

    with pytest.raises(ConfigError, match="output files must be distinct"):
        load_config(repo_root)


def test_config_rejects_casefolded_output_collision(tmp_path: Path) -> None:
    """Output names that alias on common filesystems are conservatively rejected."""

    repo_root = tmp_path / "repo"
    _write_config(
        repo_root,
        outputs={
            "index_json": ".docsync/out/RESULT.json",
            "report_json": ".docsync/out/result.json",
        },
    )

    with pytest.raises(ConfigError, match="output files must be distinct"):
        load_config(repo_root)


@pytest.mark.parametrize("reserved_name", (".gitignore", ".GITIGNORE"))
def test_config_rejects_policy_owned_output_without_changing_canary(
    tmp_path: Path,
    reserved_name: str,
) -> None:
    """Configured artifacts cannot overwrite the generated-root ignore policy."""

    repo_root = tmp_path / "repo"
    output_path = f".docsync/out/{reserved_name}"
    _write_config(repo_root, outputs={"index_json": output_path})
    policy_file = repo_root / ".docsync" / "out" / reserved_name
    policy_file.parent.mkdir(parents=True)
    policy_file.write_text("canary\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="reserved policy filename"):
        load_config(repo_root)

    assert policy_file.read_text(encoding="utf-8") == "canary\n"


def test_legacy_config_defaults_to_docsync_output_root(tmp_path: Path) -> None:
    """Legacy configs without an output directory keep their existing root."""
    repo_root = tmp_path / "repo"
    _write_config(repo_root)
    config_path = repo_root / ".docsync" / "config.yml"
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    payload["outputs"].pop("directory", None)
    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    config = load_config(repo_root)

    assert config.output_dir == repo_root / ".docsync" / "out"
    assert config.report_json == config.output_dir / "report.json"


def test_config_rejects_output_symlink_without_changing_target(tmp_path: Path) -> None:
    """An existing output symlink cannot redirect an explicit report write."""
    repo_root = tmp_path / "repo"
    outside = tmp_path / "outside.txt"
    outside.write_text("unchanged\n", encoding="utf-8")
    _write_config(repo_root)
    output_dir = repo_root / ".docsync" / "out"
    output_dir.mkdir()
    (output_dir / "report.json").symlink_to(outside)

    with pytest.raises(ConfigError, match="must not contain symlinks"):
        load_config(repo_root)

    assert outside.read_text(encoding="utf-8") == "unchanged\n"


def test_config_rejects_output_symlink_parent_before_create(tmp_path: Path) -> None:
    """A symlinked output directory cannot create files outside the repository."""
    repo_root = tmp_path / "repo"
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    _write_config(repo_root)
    (repo_root / ".docsync" / "out").symlink_to(outside_dir)

    with pytest.raises(ConfigError, match="must not contain symlinks"):
        load_config(repo_root)

    assert list(outside_dir.iterdir()) == []


@pytest.mark.parametrize("directory", ("../../attestations", "/tmp/docsync-attestations"))
def test_config_rejects_escaped_attestation_directory(
    tmp_path: Path,
    directory: str,
) -> None:
    """The repository-controlled attestation read/write root cannot escape."""
    repo_root = tmp_path / "repo"
    _write_config(repo_root, attestations_directory=directory)

    with pytest.raises(ConfigError, match=r"relative|\.\."):
        load_config(repo_root)


@pytest.mark.parametrize(
    "directory",
    (".", "src", ".github/workflows", ".docsync/out"),
)
def test_config_rejects_attestation_directory_outside_dedicated_root(
    tmp_path: Path,
    directory: str,
) -> None:
    """Attestation writes cannot target source, workflows, or generated reports."""

    repo_root = tmp_path / "repo"
    _write_config(repo_root, attestations_directory=directory)

    with pytest.raises(ConfigError, match="attestation directory must remain under"):
        load_config(repo_root)


def test_config_path_symlink_is_rejected_before_yaml_read(tmp_path: Path) -> None:
    """A custom config symlink cannot redirect YAML reads outside the repository."""
    repo_root = tmp_path / "repo"
    outside = tmp_path / "config.yml"
    repo_root.mkdir()
    outside.write_text(DEFAULT_CONFIG_TEXT, encoding="utf-8")
    (repo_root / "linked.yml").symlink_to(outside)

    with pytest.raises(ConfigError, match="must not contain symlinks"):
        load_config(repo_root, Path("linked.yml"))


def test_invalid_config_never_writes_requested_reports(tmp_path: Path) -> None:
    """Explicit report mode still refuses all writes when input validation fails."""
    repo_root = tmp_path / "repo"
    _write_config(repo_root, outputs={"report_json": "../../outside.json"})
    _write_trace(repo_root)

    result = docsync_cli.main(["--repo-root", str(repo_root), "check", "--write-reports"])

    assert result == 1
    assert not (tmp_path / "outside.json").exists()
    assert not (repo_root / ".docsync" / "out" / "report.json").exists()


def test_invalid_config_never_writes_prompt_outputs(tmp_path: Path) -> None:
    """Prompt mode does not write fallback artifacts after path validation fails."""
    repo_root = tmp_path / "repo"
    _write_config(repo_root, outputs={"review_prompt_md": "../../outside.md"})
    _write_trace(repo_root)

    result = docsync_cli.main(["--repo-root", str(repo_root), "prompt"])

    assert result == 1
    assert not (tmp_path / "outside.md").exists()
    assert not (repo_root / ".docsync" / "out" / "review-prompt.md").exists()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO creation is unavailable")
def test_report_pair_is_preflighted_before_first_write(tmp_path: Path) -> None:
    """An unsafe SARIF target prevents the earlier JSON report write."""
    repo_root = tmp_path / "repo"
    _write_empty_repo(repo_root)
    output_dir = repo_root / ".docsync" / "out"
    output_dir.mkdir()
    os.mkfifo(output_dir / "report.sarif.json")

    result = docsync_cli.main(["--repo-root", str(repo_root), "check", "--write-reports"])

    assert result == 1
    assert not (output_dir / "report.json").exists()


def test_freshness_output_must_stay_under_generated_root(tmp_path: Path) -> None:
    """The direct freshness output option cannot escape or target source files."""
    repo_root = tmp_path / "repo"
    _write_empty_repo(repo_root)

    with pytest.raises(PathBoundaryError, match=r"\.\."):
        docsync_cli.main(
            [
                "--repo-root",
                str(repo_root),
                "freshness",
                "--output",
                "../../outside.json",
            ]
        )

    assert not (tmp_path / "outside.json").exists()


def test_freshness_output_cannot_replace_generated_root(tmp_path: Path) -> None:
    """A direct freshness output must be a file below the configured directory."""

    repo_root = tmp_path / "repo"
    _write_empty_repo(repo_root)

    with pytest.raises(PathBoundaryError, match="must be a file below"):
        docsync_cli.main(
            [
                "--repo-root",
                str(repo_root),
                "freshness",
                "--output",
                ".docsync/out",
            ]
        )


def test_freshness_output_cannot_replace_policy_file(tmp_path: Path) -> None:
    """Direct freshness output preserves the generated-root ignore policy."""

    repo_root = tmp_path / "repo"
    _write_empty_repo(repo_root)
    policy_file = repo_root / ".docsync" / "out" / ".gitignore"
    policy_file.parent.mkdir(parents=True)
    policy_file.write_text("canary\n", encoding="utf-8")

    with pytest.raises(PathBoundaryError, match="reserved policy filename"):
        docsync_cli.main(
            [
                "--repo-root",
                str(repo_root),
                "freshness",
                "--output",
                ".docsync/out/.gitignore",
            ]
        )

    assert policy_file.read_text(encoding="utf-8") == "canary\n"


def test_trace_authoring_rejects_paths_before_any_mutation(tmp_path: Path) -> None:
    """A rejected trace or source path leaves both trace and outside source unchanged."""
    repo_root = tmp_path / "repo"
    outside_trace = tmp_path / "outside-trace.yml"
    source = repo_root / "README.md"
    _write_empty_repo(repo_root)
    source.write_text("# Demo\n", encoding="utf-8")
    outside_trace.write_text(
        "version: 1\ndocuments: {}\nobjects: {}\nclaims: {}\nevidence: {}\n",
        encoding="utf-8",
    )
    trace_path = repo_root / ".docsync" / "trace.yml"
    before_trace = trace_path.read_text(encoding="utf-8")

    result = docsync_cli.main(
        [
            "--repo-root",
            str(repo_root),
            "trace",
            "add-object",
            "docs.demo",
            "--trace",
            "../../outside-trace.yml",
            "--document",
            "docs.readme",
            "--path",
            "README.md",
            "--marker",
            "docs.demo",
            "--insert-marker",
        ]
    )

    assert result == 1
    assert trace_path.read_text(encoding="utf-8") == before_trace
    assert source.read_text(encoding="utf-8") == "# Demo\n"
    assert "objects: {}" in outside_trace.read_text(encoding="utf-8")


def test_trace_authoring_rejects_outside_source_before_trace_write(tmp_path: Path) -> None:
    """An escaped source option cannot alter either the source or trace YAML."""
    repo_root = tmp_path / "repo"
    outside_source = tmp_path / "outside.py"
    _write_empty_repo(repo_root)
    outside_source.write_text("outside behavior\n", encoding="utf-8")
    trace_path = repo_root / ".docsync" / "trace.yml"
    before_trace = trace_path.read_text(encoding="utf-8")

    result = docsync_cli.main(
        [
            "--repo-root",
            str(repo_root),
            "trace",
            "add-evidence",
            "evidence.demo",
            "--path",
            "../../outside.py",
            "--type",
            "code",
            "--insert-region",
        ]
    )

    assert result == 1
    assert trace_path.read_text(encoding="utf-8") == before_trace
    assert outside_source.read_text(encoding="utf-8") == "outside behavior\n"


def _write_empty_repo(repo_root: Path) -> None:
    _write_config(repo_root)
    _write_trace(repo_root)


def _write_config(
    repo_root: Path,
    *,
    outputs: dict[str, str] | None = None,
    attestations_directory: str | None = None,
) -> None:
    docsync_root = repo_root / ".docsync"
    docsync_root.mkdir(parents=True, exist_ok=True)
    payload = yaml.safe_load(DEFAULT_CONFIG_TEXT)
    if outputs:
        payload["outputs"].update(outputs)
    if attestations_directory is not None:
        payload["attestations"]["directory"] = attestations_directory
    (docsync_root / "config.yml").write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def _write_trace(
    repo_root: Path,
    *,
    documents: dict[str, Any] | None = None,
    objects: dict[str, Any] | None = None,
    claims: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
) -> None:
    payload = {
        "version": 1,
        "documents": documents or {},
        "objects": objects or {},
        "claims": claims or {},
        "evidence": evidence or {},
    }
    (repo_root / ".docsync" / "trace.yml").write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
