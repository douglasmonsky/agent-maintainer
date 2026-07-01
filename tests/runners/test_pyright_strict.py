"""Tests for strict Pyright ratchet runner helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.runners import pyright_strict

BASELINE_ERRORS = 10
BUDGETED_ERRORS = 11
REGRESSED_ERRORS = 12
SAMPLE_ERRORS = 3
SAMPLE_FILES = 2
ZERO_ERRORS = 0


def test_strict_pyright_config_forces_strict_mode() -> None:
    """Strict runner uses strict mode without changing normal config object."""

    config = MaintainerConfig(pyright_type_checking_mode="standard")

    strict_config = pyright_strict.strict_pyright_config(config)

    assert config.pyright_type_checking_mode == "standard"
    assert strict_config.pyright_type_checking_mode == "strict"


def test_stats_from_payload_groups_strict_errors_by_rule_and_file() -> None:
    """Pyright JSON diagnostics are grouped for compact summaries."""

    stats = pyright_strict.stats_from_payload(
        {
            "summary": {"errorCount": SAMPLE_ERRORS, "filesAnalyzed": SAMPLE_FILES},
            "generalDiagnostics": [
                {
                    "severity": "error",
                    "file": "src/example.py",
                    "rule": "reportUnknownMemberType",
                },
                {
                    "severity": "error",
                    "file": "src/example.py",
                    "rule": "reportUnknownMemberType",
                },
                {
                    "severity": "error",
                    "file": "tests/test_example.py",
                    "rule": "reportUnknownArgumentType",
                },
                {
                    "severity": "warning",
                    "file": "src/example.py",
                    "rule": "reportUnusedImport",
                },
            ],
        },
    )

    assert stats.total_errors == SAMPLE_ERRORS
    assert stats.files_analyzed == SAMPLE_FILES
    assert stats.by_rule == {
        "reportUnknownArgumentType": 1,
        "reportUnknownMemberType": 2,
    }
    assert stats.by_file == {"src/example.py": 2, "tests/test_example.py": 1}


def test_compare_stats_allows_current_baseline() -> None:
    """Strict ratchet passes when current error count stays within baseline."""

    result = pyright_strict.compare_stats(
        pyright_strict.StrictPyrightStats(
            total_errors=BASELINE_ERRORS,
            files_analyzed=2,
            by_rule={"reportUnknownMemberType": BASELINE_ERRORS},
            by_file={"src/example.py": BASELINE_ERRORS},
        ),
        pyright_strict.StrictBaseline(
            total_errors=BASELINE_ERRORS,
            by_rule={"reportUnknownMemberType": BASELINE_ERRORS},
        ),
        extra_error_budget=0,
    )

    assert result.passed is True
    assert result.allowed_errors == BASELINE_ERRORS


def test_compare_stats_fails_above_baseline_budget() -> None:
    """Strict ratchet fails only when total diagnostics regress past budget."""

    result = pyright_strict.compare_stats(
        pyright_strict.StrictPyrightStats(
            total_errors=REGRESSED_ERRORS,
            files_analyzed=2,
            by_rule={"reportUnknownMemberType": REGRESSED_ERRORS},
            by_file={"src/example.py": REGRESSED_ERRORS},
        ),
        pyright_strict.StrictBaseline(
            total_errors=BASELINE_ERRORS,
            by_rule={"reportUnknownMemberType": BASELINE_ERRORS},
        ),
        extra_error_budget=1,
    )

    assert result.passed is False
    assert result.allowed_errors == BUDGETED_ERRORS


def test_load_baseline_reads_committed_shape(tmp_path: Path) -> None:
    """Baseline JSON uses a small stable shape."""

    baseline_path = tmp_path / "pyright-strict-baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "version": 1,
                "total_errors": SAMPLE_ERRORS,
                "by_rule": {"reportUnknownMemberType": SAMPLE_ERRORS},
            },
        ),
        encoding="utf-8",
    )

    baseline = pyright_strict.load_baseline(baseline_path)

    assert baseline == pyright_strict.StrictBaseline(
        total_errors=SAMPLE_ERRORS,
        by_rule={"reportUnknownMemberType": SAMPLE_ERRORS},
    )


def test_format_result_is_summary_first() -> None:
    """Strict result summary includes totals and grouped diagnostics."""

    result = pyright_strict.StrictRatchetResult(
        passed=False,
        current=pyright_strict.StrictPyrightStats(
            total_errors=REGRESSED_ERRORS,
            files_analyzed=SAMPLE_FILES,
            by_rule={"reportUnknownMemberType": REGRESSED_ERRORS},
            by_file={"src/example.py": REGRESSED_ERRORS},
        ),
        baseline=pyright_strict.StrictBaseline(
            total_errors=BASELINE_ERRORS,
            by_rule={"reportUnknownMemberType": BASELINE_ERRORS},
        ),
        allowed_errors=BASELINE_ERRORS,
    )

    summary = pyright_strict.format_result(result)

    assert f"pyright strict ratchet failed: {REGRESSED_ERRORS} errors" in summary
    assert f"- reportUnknownMemberType: {REGRESSED_ERRORS}" in summary
    assert f"- src/example.py: {REGRESSED_ERRORS}" in summary
    assert "Repair:" in summary


def test_main_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Disabled strict ratchet exits successfully with compact message."""

    monkeypatch.setattr(pyright_strict, "load_config", MaintainerConfig)

    assert pyright_strict.main() == 0
    assert "skipped: disabled" in capsys.readouterr().out


def test_run_strict_ratchet_passes_within_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Runner returns success when current strict errors meet baseline."""

    config = MaintainerConfig(
        diagnostic_artifacts_dir=str(tmp_path),
        pyright_strict_baseline=str(tmp_path / "baseline.json"),
        pyright_strict_ratchet_enabled=True,
    )
    monkeypatch.setattr(pyright_strict, "run_pyright_json", clean_pyright_payload)
    monkeypatch.setattr(pyright_strict, "load_baseline", zero_baseline)

    assert pyright_strict.run_strict_ratchet(config) == 0
    assert "pyright strict ratchet passed" in capsys.readouterr().out


def test_run_strict_ratchet_fails_above_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runner fails when current strict errors exceed baseline."""

    config = MaintainerConfig(
        diagnostic_artifacts_dir=str(tmp_path),
        pyright_strict_baseline=str(tmp_path / "baseline.json"),
        pyright_strict_ratchet_enabled=True,
    )
    monkeypatch.setattr(pyright_strict, "run_pyright_json", sample_pyright_payload)
    monkeypatch.setattr(pyright_strict, "load_baseline", zero_baseline)

    assert pyright_strict.run_strict_ratchet(config) == 1


def test_run_strict_ratchet_fails_for_missing_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runner fails when Pyright output cannot be parsed."""

    config = MaintainerConfig(
        diagnostic_artifacts_dir=str(tmp_path),
        pyright_strict_ratchet_enabled=True,
    )
    monkeypatch.setattr(pyright_strict, "run_pyright_json", missing_pyright_payload)

    assert pyright_strict.run_strict_ratchet(config) == 1


def test_run_strict_ratchet_fails_for_zero_analyzed_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runner rejects generated configs that analyze no files."""

    config = MaintainerConfig(
        diagnostic_artifacts_dir=str(tmp_path),
        pyright_strict_baseline=str(tmp_path / "baseline.json"),
        pyright_strict_ratchet_enabled=True,
    )
    monkeypatch.setattr(pyright_strict, "run_pyright_json", zero_file_pyright_payload)
    monkeypatch.setattr(pyright_strict, "load_baseline", zero_baseline)

    assert pyright_strict.run_strict_ratchet(config) == 1


def test_run_pyright_json_reports_invalid_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid Pyright JSON returns no payload."""

    monkeypatch.setattr(pyright_strict.shutil, "which", fake_which)
    monkeypatch.setattr(
        pyright_strict.subprocess,
        "run",
        invalid_json_run,
    )

    assert pyright_strict.run_pyright_json(tmp_path / "config.json", tmp_path / "out.json") is None


def test_run_pyright_json_reports_runner_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected Pyright exit code returns no payload."""

    monkeypatch.setattr(pyright_strict.shutil, "which", fake_which)
    monkeypatch.setattr(
        pyright_strict.subprocess,
        "run",
        failed_pyright_run,
    )

    assert pyright_strict.run_pyright_json(tmp_path / "config.json", tmp_path / "out.json") is None


def test_load_baseline_rejects_invalid_shapes(tmp_path: Path) -> None:
    """Baseline loader rejects missing, malformed, and non-integer counts."""

    assert pyright_strict.load_baseline(tmp_path / "missing.json") is None
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    assert pyright_strict.load_baseline(malformed) is None
    invalid = tmp_path / "invalid.json"
    invalid.write_text(
        json.dumps({"total_errors": 1, "by_rule": {"rule": "many"}}),
        encoding="utf-8",
    )
    assert pyright_strict.load_baseline(invalid) is None


def test_json_helpers_handle_missing_shapes() -> None:
    """JSON helper edge cases stay deterministic."""

    assert pyright_strict.diagnostic_errors({"generalDiagnostics": "bad"}) == []
    assert pyright_strict.summary_payload({"summary": "bad"}) == {}
    assert pyright_strict.normalize_file(None) == "<unknown>"
    assert pyright_strict.signed_number(0) == "+0"
    assert pyright_strict.signed_number(-1) == "-1"
    assert pyright_strict.format_top_counts({}) == ["- none"]


def clean_pyright_payload(_config_path: Path, _output_path: Path) -> dict[str, object]:
    """Return clean payload for monkeypatched strict Pyright run."""

    return clean_payload()


def sample_pyright_payload(_config_path: Path, _output_path: Path) -> dict[str, object]:
    """Return sample payload for monkeypatched strict Pyright run."""

    return sample_payload()


def missing_pyright_payload(_config_path: Path, _output_path: Path) -> None:
    """Return missing payload for monkeypatched strict Pyright run."""

    return None


def zero_file_pyright_payload(
    _config_path: Path,
    _output_path: Path,
) -> dict[str, object]:
    """Return payload showing no analyzed files."""

    return {"summary": {"errorCount": ZERO_ERRORS, "filesAnalyzed": ZERO_ERRORS}}


def zero_baseline(_path: Path) -> pyright_strict.StrictBaseline:
    """Return empty baseline for runner tests."""

    return pyright_strict.StrictBaseline(total_errors=ZERO_ERRORS, by_rule={})


def fake_which(_name: str) -> str:
    """Return fake Pyright executable."""

    return "pyright"


def invalid_json_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
    """Return subprocess result with invalid JSON stdout."""

    return subprocess.CompletedProcess(
        args=["pyright"],
        returncode=1,
        stdout="not-json",
        stderr="bad",
    )


def failed_pyright_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
    """Return subprocess result with unexpected Pyright failure."""

    return subprocess.CompletedProcess(
        args=["pyright"],
        returncode=SAMPLE_FILES,
        stdout=json.dumps(clean_payload()),
        stderr="bad",
    )


def clean_payload() -> dict[str, object]:
    """Return strict Pyright payload with no errors."""

    return {"summary": {"errorCount": ZERO_ERRORS, "filesAnalyzed": SAMPLE_FILES}}


def sample_payload() -> dict[str, object]:
    """Return strict Pyright payload with sample errors."""

    return {
        "summary": {"errorCount": SAMPLE_ERRORS, "filesAnalyzed": SAMPLE_FILES},
        "generalDiagnostics": [
            {
                "severity": "error",
                "file": "src/example.py",
                "rule": "reportUnknownMemberType",
            },
        ],
    }
