"""Adversarial DocSync input and attestation read tests."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from docsync.attestations import files as attestation_files
from docsync.attestations.load import load_attestations
from docsync.config.defaults import DEFAULT_CONFIG_TEXT
from docsync.config.io import MAX_REPOSITORY_INPUT_BYTES, read_bounded_text
from docsync.config.load import ConfigError, load_config
from docsync.config.paths import PathBoundaryError
from docsync.indexer import build_docsync_index
from docsync.trace import load as trace_load
from docsync.trace.load import TraceError, load_trace


@pytest.mark.parametrize(
    "configured_path",
    (
        "../../secret.md",
        "/tmp/docsync-secret.md",
        ".docker/config.json",
        ".env",
        ".envrc",
        ".git-credentials",
        ".git/config",
        ".kube/config",
        "private-key.pem",
        "secrets.yaml",
    ),
)
def test_trace_rejects_escaped_or_sensitive_document_paths(
    tmp_path: Path,
    configured_path: str,
) -> None:
    """Trace-controlled document paths fail before document content is opened."""
    repo_root = tmp_path / "repo"
    _write_empty_repo(repo_root)
    _write_trace(repo_root, documents={"docs.demo": {"path": configured_path}})

    with pytest.raises(TraceError, match=r"relative|\.\.|sensitive"):
        load_trace(repo_root)


def test_trace_rejects_symlinked_document_before_outside_read(tmp_path: Path) -> None:
    """A trace document symlink cannot expose an outside file."""
    repo_root = tmp_path / "repo"
    outside = tmp_path / "secret.md"
    outside.write_text("outside secret\n", encoding="utf-8")
    _write_empty_repo(repo_root)
    (repo_root / "linked.md").symlink_to(outside)
    _write_trace(repo_root, documents={"docs.demo": {"path": "linked.md"}})

    with pytest.raises(TraceError, match="must not contain symlinks"):
        load_trace(repo_root)


def test_trace_rejects_symlinked_evidence_parent(tmp_path: Path) -> None:
    """A trace evidence parent symlink cannot escape the repository."""
    repo_root = tmp_path / "repo"
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "source.py").write_text("secret\n", encoding="utf-8")
    _write_empty_repo(repo_root)
    (repo_root / "linked").symlink_to(outside_dir, target_is_directory=True)
    _write_trace(
        repo_root,
        evidence={
            "evidence.demo": {
                "type": "code",
                "anchors": [{"path": "linked/source.py", "mode": "explicit_region"}],
            }
        },
    )

    with pytest.raises(TraceError, match="must not contain symlinks"):
        load_trace(repo_root)


def test_trace_rejects_sparse_oversized_input(tmp_path: Path) -> None:
    """Sparse inputs are refused from metadata before their content is read."""
    repo_root = tmp_path / "repo"
    _write_empty_repo(repo_root)
    oversized = repo_root / "oversized.md"
    with oversized.open("wb") as handle:
        handle.seek(MAX_REPOSITORY_INPUT_BYTES)
        handle.write(b"x")
    _write_trace(repo_root, documents={"docs.demo": {"path": "oversized.md"}})

    with pytest.raises(TraceError, match="exceeds"):
        load_trace(repo_root)


def test_trace_file_is_read_once_for_payload_and_line_spans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trace parsing reuses the bounded text instead of reopening the YAML."""
    repo_root = tmp_path / "repo"
    _write_empty_repo(repo_root)
    trace_path = repo_root / ".docsync" / "trace.yml"
    calls: list[Path] = []
    original = trace_load.read_bounded_text

    def tracked_read(
        path: Path,
        *,
        label: str,
        max_bytes: int = MAX_REPOSITORY_INPUT_BYTES,
    ) -> str:
        calls.append(path)
        return original(path, label=label, max_bytes=max_bytes)

    monkeypatch.setattr(trace_load, "read_bounded_text", tracked_read)

    load_trace(repo_root)

    assert calls.count(trace_path) == 1


def test_trace_rejects_excessive_aggregate_source_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Many individually valid files cannot bypass the aggregate read ceiling."""
    repo_root = tmp_path / "repo"
    _write_empty_repo(repo_root)
    (repo_root / "large.md").write_text("0123456789\n", encoding="utf-8")
    _write_trace(repo_root, documents={"docs.large": {"path": "large.md"}})
    monkeypatch.setattr(trace_load, "MAX_TRACE_SOURCE_BYTES", 8)

    with pytest.raises(TraceError, match="aggregate limit"):
        load_trace(repo_root)


@pytest.mark.parametrize("filename", ("config.yml", "trace.yml"))
def test_yaml_inputs_are_size_bounded(tmp_path: Path, filename: str) -> None:
    """Configuration and trace YAML use the same bounded regular-file reader."""
    repo_root = tmp_path / "repo"
    _write_empty_repo(repo_root)
    oversized = repo_root / ".docsync" / filename
    with oversized.open("wb") as handle:
        handle.seek(MAX_REPOSITORY_INPUT_BYTES)
        handle.write(b"x")

    if filename == "config.yml":
        with pytest.raises(ConfigError, match="exceeds"):
            load_config(repo_root)
    else:
        with pytest.raises(TraceError, match="exceeds"):
            load_trace(repo_root)


@pytest.mark.parametrize(
    "payload",
    (
        "outputs: [\n",
        "value: " + "[" * 1000 + "]" * 1000,
    ),
)
def test_config_normalizes_yaml_parser_failures(tmp_path: Path, payload: str) -> None:
    """Malformed and deeply nested config YAML produce a stable domain error."""

    repo_root = tmp_path / "repo"
    _write_empty_repo(repo_root)
    (repo_root / ".docsync" / "config.yml").write_text(payload, encoding="utf-8")

    with pytest.raises(ConfigError, match="Cannot parse DocSync YAML"):
        load_config(repo_root)


@pytest.mark.parametrize(
    "payload",
    (
        "documents: [\n",
        "value: " + "[" * 1000 + "]" * 1000,
    ),
)
def test_trace_normalizes_yaml_parser_failures(tmp_path: Path, payload: str) -> None:
    """Malformed and deeply nested trace YAML produce a stable trace error."""

    repo_root = tmp_path / "repo"
    _write_empty_repo(repo_root)
    (repo_root / ".docsync" / "trace.yml").write_text(payload, encoding="utf-8")

    with pytest.raises(TraceError, match="Cannot parse DocSync YAML"):
        load_trace(repo_root)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO creation is unavailable")
def test_fifo_is_refused_without_blocking(tmp_path: Path) -> None:
    """The bounded reader opens special files nonblocking and then refuses them."""
    fifo = tmp_path / "input.yml"
    os.mkfifo(fifo)

    with pytest.raises(PathBoundaryError, match="regular file"):
        read_bounded_text(fifo, label="test FIFO")


def test_symlinked_attestation_is_not_opened(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each globbed attestation is independently confined before YAML loading."""
    repo_root = tmp_path / "repo"
    outside = tmp_path / "outside.yml"
    outside.write_text("attestations: []\n", encoding="utf-8")
    _write_empty_repo(repo_root)
    attestations_dir = repo_root / ".docsync" / "attestations"
    attestations_dir.mkdir()
    (attestations_dir / "linked.yml").symlink_to(outside)
    index = build_docsync_index(repo_root)
    opened: list[Path] = []
    real_open = os.open

    def recording_open(path: Any, flags: int, mode: int = 0o777) -> int:
        opened.append(Path(path))
        return real_open(path, flags, mode)

    monkeypatch.setattr(os, "open", recording_open)

    result = load_attestations(index)

    assert [finding.code for finding in result.findings] == ["DS301"]
    assert all(path.name != "linked.yml" for path in opened)


def test_attestation_discovery_reports_deterministic_bounded_overflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Discovery retains only a sorted bounded prefix and identifies its overflow."""

    repo_root = tmp_path / "repo"
    _write_empty_repo(repo_root)
    directory = repo_root / ".docsync" / "attestations"
    directory.mkdir()
    for name in ("z.yml", "b.yaml", "c.yml", "a.yml"):
        (directory / name).write_text("attestations: []\n", encoding="utf-8")
    monkeypatch.setattr(attestation_files, "MAX_ATTESTATION_FILES", 2)
    index = build_docsync_index(repo_root)

    result = load_attestations(index)

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "DS301"
    assert finding.message == "Attestation file limit exceeded: 2."
    assert finding.locations[0].path == directory / "c.yml"


def _write_empty_repo(repo_root: Path) -> None:
    _write_config(repo_root)
    _write_trace(repo_root)


def _write_config(repo_root: Path) -> None:
    docsync_root = repo_root / ".docsync"
    docsync_root.mkdir(parents=True, exist_ok=True)
    (docsync_root / "config.yml").write_text(DEFAULT_CONFIG_TEXT, encoding="utf-8")


def _write_trace(
    repo_root: Path,
    *,
    documents: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
) -> None:
    payload = {
        "version": 1,
        "documents": documents or {},
        "objects": {},
        "claims": {},
        "evidence": evidence or {},
    }
    (repo_root / ".docsync" / "trace.yml").write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
