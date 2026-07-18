"""Public contract command exit and write-safety tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from agent_maintainer.contracts import cli
from agent_maintainer.contracts.baseline import DEFAULT_BASELINE_PATH
from agent_maintainer.contracts.models import (
    ContractBaseline,
    ContractChange,
    ContractReport,
    Descriptor,
)
from agent_maintainer.contracts.reporting import render_json


def _descriptor() -> Descriptor:
    return Descriptor(
        contract_id="public-api",
        kind="python-api",
        owner="agent_maintainer.api",
        stability="beta",
        revision=2,
        sources=("src/agent_maintainer/api.py",),
        body={"exports": [{"kind": "function", "name": "run"}]},
        fingerprint="sha256:" + "a" * 64,
    )


def _blocked_report(*, invalid: bool = False) -> ContractReport:
    fingerprint = "sha256:" + "b" * 64
    return ContractReport(
        mode="check",
        base_ref="origin/main",
        current_package_version="0.1.0b10",
        descriptors=(_descriptor(),),
        changes=(
            ContractChange(
                contract_id="public-api",
                operation="unsupported-semantic-change",
                path="/exports/run",
                before="old",
                after="new",
                classification="review-required",
                fingerprint=fingerprint,
                reason="compatibility is not provable",
            ),
        ),
        errors=("invalid policy",) if invalid else (),
    )


def _clean_report(*, mode: str = "check") -> ContractReport:
    return ContractReport(
        mode=mode,
        base_ref="origin/main",
        current_package_version="0.1.0b10",
        descriptors=(_descriptor(),),
        can_snapshot=True,
    )


def _report_builder(
    report: ContractReport,
) -> Callable[..., ContractReport]:
    def build(
        _target: Path,
        *,
        base_ref: str,
        mode: str,
        initialize: bool = False,
    ) -> ContractReport:
        del base_ref, mode, initialize
        return report

    return build


def _ignore_baseline_write(
    _root: Path,
    _path: Path,
    _baseline: ContractBaseline,
) -> None:
    return None


def test_snapshot_requires_explicit_write(capsys: pytest.CaptureFixture[str]) -> None:
    """Snapshot never treats an omitted mutation flag as consent."""
    status = cli.main(["snapshot"])

    assert status == cli.INVALID
    assert "snapshot requires --write" in capsys.readouterr().err


def test_diff_is_advisory_with_breaking_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Diff renders unresolved facts without enforcing them."""
    monkeypatch.setattr(cli, "build_contract_report", _report_builder(_blocked_report()))

    assert cli.main(["diff", "--json"]) == 0


@pytest.mark.parametrize(
    ("report", "expected"),
    (
        (_clean_report(), cli.SUCCESS),
        (_blocked_report(), cli.UNRESOLVED),
        (_blocked_report(invalid=True), cli.INVALID),
    ),
)
def test_check_exit_statuses(
    monkeypatch: pytest.MonkeyPatch,
    report: ContractReport,
    expected: int,
) -> None:
    """Check distinguishes clean, unresolved, and invalid reports."""
    monkeypatch.setattr(cli, "build_contract_report", _report_builder(report))

    assert cli.main(["check"]) == expected


def test_json_output_exactly_matches_reporting_layer(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI JSON stays complete for run-scoped captured logs."""
    report = _blocked_report()
    monkeypatch.setattr(cli, "build_contract_report", _report_builder(report))

    assert cli.main(["check", "--json"]) == 1
    assert capsys.readouterr().out == render_json(report)


def test_default_and_custom_base_refs_reach_service(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Every public command supplies an explicit root and base-ref identity."""
    calls: list[tuple[Path, str, str, bool]] = []

    def build(
        target: Path,
        *,
        base_ref: str,
        mode: str,
        initialize: bool = False,
    ) -> ContractReport:
        calls.append((target, base_ref, mode, initialize))
        return _clean_report(mode=mode)

    monkeypatch.setattr(cli, "build_contract_report", build)

    assert cli.main(["diff", "--target", str(tmp_path)]) == 0
    assert cli.main(["check", "--target", str(tmp_path), "--base-ref", "release"]) == 0
    assert calls == [
        (tmp_path.resolve(), "origin/main", "diff", False),
        (tmp_path.resolve(), "release", "check", False),
    ]


def test_diff_and_check_never_write_baseline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Read-only commands never call the generated evidence writer."""
    monkeypatch.setattr(cli, "build_contract_report", _report_builder(_clean_report()))

    def unexpected_write(*_args: object, **_kwargs: object) -> None:
        pytest.fail("read-only contract command attempted a baseline write")

    monkeypatch.setattr(cli, "write_baseline_atomic", unexpected_write)

    assert cli.main(["diff", "--target", str(tmp_path)]) == 0
    assert cli.main(["check", "--target", str(tmp_path)]) == 0


def test_snapshot_refuses_unresolved_report_without_writing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit write intent cannot bypass unresolved obligations."""
    monkeypatch.setattr(cli, "build_contract_report", _report_builder(_blocked_report()))
    writes = 0

    def unexpected_write(*_args: object, **_kwargs: object) -> None:
        nonlocal writes
        writes += 1

    monkeypatch.setattr(cli, "write_baseline_atomic", unexpected_write)

    assert cli.main(["snapshot", "--write"]) == 1
    assert writes == 0


def test_snapshot_writes_prospective_baseline_atomically(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A clean snapshot writes exact live descriptors and package version."""
    report = _clean_report(mode="snapshot")
    monkeypatch.setattr(cli, "build_contract_report", _report_builder(report))
    writes: list[tuple[Path, Path, ContractBaseline]] = []

    def record_write(root: Path, path: Path, baseline: ContractBaseline) -> None:
        writes.append((root, path, baseline))

    monkeypatch.setattr(cli, "write_baseline_atomic", record_write)

    assert cli.main(["snapshot", "--write", "--target", str(tmp_path)]) == 0
    assert len(writes) == 1
    root, path, baseline = writes[0]
    assert root == tmp_path.resolve()
    assert path == DEFAULT_BASELINE_PATH
    assert baseline.package_version == "0.1.0b10"
    assert baseline.descriptors == (_descriptor(),)


def test_snapshot_passes_initialization_and_relative_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Initialization and relative targets remain explicit at the service boundary."""
    repository = tmp_path / "repo"
    repository.mkdir()
    monkeypatch.chdir(tmp_path)
    calls: list[tuple[Path, bool]] = []

    def build(
        target: Path,
        *,
        base_ref: str,
        mode: str,
        initialize: bool = False,
    ) -> ContractReport:
        assert base_ref == "origin/main"
        assert mode == "snapshot"
        calls.append((target, initialize))
        return _clean_report(mode="snapshot")

    monkeypatch.setattr(cli, "build_contract_report", build)
    monkeypatch.setattr(cli, "write_baseline_atomic", _ignore_baseline_write)

    assert cli.main(["snapshot", "--write", "--initialize", "--target", "repo"]) == 0
    assert calls == [(repository.resolve(), True)]
