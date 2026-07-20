"""Tests for mutation-target survivor contracts."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel.mutation import targets as mutation_targets


def test_mutation_target_report_defaults_missing_metadata_to_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Report construction preserves zero defaults and explicit target sorting."""

    config = MaintainerConfig(source_roots=("src",), test_roots=("tests",))
    source_paths = ("src/pkg/low.py", "src/pkg/high.py")
    calls: list[tuple[str, int, int]] = []

    def fake_discover_source_files(
        config: MaintainerConfig,
        repo_root: Path,
    ) -> tuple[str, ...]:
        del config, repo_root
        return source_paths

    def fake_likely_test_counts(
        paths: tuple[str, ...],
        config: MaintainerConfig,
        repo_root: Path,
    ) -> dict[str, int]:
        del paths, config, repo_root
        return {"src/pkg/high.py": 2}

    def fake_ratchet_path_scores(
        config: MaintainerConfig,
        repo_root: Path,
        base_ref: str,
        changed_paths: frozenset[str],
    ) -> dict[str, int]:
        del config, repo_root, base_ref, changed_paths
        return {"src/pkg/high.py": 6}

    monkeypatch.setattr(
        mutation_targets.hypothesis_candidates,
        "discover_source_files",
        fake_discover_source_files,
    )
    monkeypatch.setattr(
        mutation_targets.hypothesis_candidates,
        "likely_test_counts",
        fake_likely_test_counts,
    )
    monkeypatch.setattr(
        mutation_targets,
        "ratchet_path_scores",
        fake_ratchet_path_scores,
    )

    def fake_targets_for_source(
        source_path: str,
        repo_root: Path,
        *,
        changed: bool,
        likely_test_count: int,
        ratchet_score: int,
    ) -> tuple[mutation_targets.MutationTarget, ...]:
        del repo_root, changed
        calls.append((source_path, likely_test_count, ratchet_score))
        score = 4 if source_path.endswith("low.py") else 12
        return (
            mutation_targets.MutationTarget(
                path=source_path,
                qualname="target",
                score=score,
                complexity=1,
                reasons=("ranked",),
                suggested_focus="focus",
            ),
        )

    monkeypatch.setattr(
        mutation_targets,
        "targets_for_source",
        fake_targets_for_source,
    )

    report = mutation_targets.build_mutation_target_report(
        mutation_targets.MutationTargetRequest(
            config=config,
            repo_root=tmp_path,
            changed_only=False,
            ratchet_enabled=True,
            base_ref="origin/main",
        )
    )

    assert calls == [
        ("src/pkg/low.py", 0, 0),
        ("src/pkg/high.py", 2, 6),
    ]
    assert [target.path for target in report.targets] == [
        "src/pkg/high.py",
        "src/pkg/low.py",
    ]


def test_ratchet_path_scores_reads_existing_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ratchet boost scoring reads baseline and filters non-boost statuses."""

    baseline_path = tmp_path / ".agent-maintainer" / "ratchet-baseline.json"
    baseline_path.parent.mkdir()
    baseline_path.write_text("{}", encoding="utf-8")
    config = MaintainerConfig(
        source_roots=("src",),
        test_roots=("tests",),
        ratchet_baseline_path=".agent-maintainer/ratchet-baseline.json",
    )
    baseline_marker = object()
    report_marker = object()
    ranked_calls: list[tuple[object, set[str], int]] = []

    def fake_status_report(baseline: object, *, base_ref: str) -> object:
        assert baseline is baseline_marker
        assert base_ref == "origin/main"
        return report_marker

    def fake_ranked_targets(
        report: object,
        *,
        changed_path_set: set[str],
        limit: int,
    ) -> tuple[SimpleNamespace, ...]:
        ranked_calls.append((report, changed_path_set, limit))
        return (
            SimpleNamespace(path="src/pkg/new.py", status="new"),
            SimpleNamespace(path="src/pkg/improved.py", status="improved"),
            SimpleNamespace(path="src/pkg/resolved.py", status="resolved"),
        )

    def fake_read_baseline(path: Path) -> object:
        assert path == baseline_path
        return baseline_marker

    monkeypatch.setattr(
        mutation_targets,
        "read_baseline",
        fake_read_baseline,
    )
    monkeypatch.setattr(mutation_targets, "status_report", fake_status_report)
    monkeypatch.setattr(mutation_targets, "ranked_targets", fake_ranked_targets)

    scores = mutation_targets.ratchet_path_scores(
        config,
        tmp_path,
        "origin/main",
        frozenset(("src/pkg/changed.py",)),
    )

    assert scores == {
        "src/pkg/new.py": mutation_targets.ratchet_status_score("new"),
        "src/pkg/improved.py": mutation_targets.ratchet_status_score("improved"),
    }
    assert ranked_calls == [(report_marker, {"src/pkg/changed.py"}, mutation_targets.RATCHET_LIMIT)]


def test_targets_for_source_reads_utf8_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source discovery pins the encoding used for repository files."""

    source_file = tmp_path / "src" / "pkg" / "module.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        "def parse_value(value: int) -> int:\n    return value\n",
        encoding="utf-8",
    )
    original_read_text = Path.read_text
    encodings: list[str | None] = []

    def record_read_text(
        path: Path,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> str:
        if path == source_file:
            encodings.append(encoding)
        return original_read_text(path, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, "read_text", record_read_text)

    mutation_targets.targets_for_source(
        "src/pkg/module.py",
        tmp_path,
        changed=True,
        likely_test_count=1,
        ratchet_score=0,
    )

    assert encodings == ["utf-8"]
