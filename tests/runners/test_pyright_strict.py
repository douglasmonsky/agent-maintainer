"""Tests for strict Pyright ratchet runner helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.runners import pyright_strict
from agent_maintainer.runners import pyright_strict_baseline as strict_baseline

SAMPLE_ERRORS = 3
SAMPLE_FILES = 2
ZERO_ERRORS = 0
PYRIGHT_VERSION = "1.1.410"
SCOPE_SHA256 = "a" * 64


def test_strict_pyright_config_forces_strict_mode() -> None:
    """Strict runner uses strict mode without changing normal config object."""

    config = MaintainerConfig(pyright_type_checking_mode="standard")

    strict_config = pyright_strict.strict_pyright_config(config)

    assert config.pyright_type_checking_mode == "standard"
    assert strict_config.pyright_type_checking_mode == "strict"


def test_stats_from_payload_groups_strict_errors_by_rule_and_file(tmp_path: Path) -> None:
    """Pyright JSON diagnostics are grouped for compact summaries."""

    stats = pyright_strict.stats_from_payload(
        {
            "version": PYRIGHT_VERSION,
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
        scope=sample_scope(tmp_path),
    )

    assert stats.total_errors == SAMPLE_ERRORS
    assert stats.files_analyzed == SAMPLE_FILES
    assert stats.by_rule == {
        "reportUnknownArgumentType": 1,
        "reportUnknownMemberType": 2,
    }
    assert stats.by_file == {"src/example.py": 2, "tests/test_example.py": 1}


def test_main_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Disabled strict ratchet exits successfully with compact message."""

    monkeypatch.setattr(pyright_strict.maintainer_config, "load_config", MaintainerConfig)

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
    monkeypatch.setattr(pyright_strict.strict_baseline, "load_baseline", zero_baseline)
    monkeypatch.setattr(pyright_strict, "scope_from_config", fixed_scope)

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
    monkeypatch.setattr(pyright_strict.strict_baseline, "load_baseline", zero_baseline)
    monkeypatch.setattr(pyright_strict, "scope_from_config", fixed_scope)

    assert pyright_strict.run_strict_ratchet(config) == 1


def test_run_strict_ratchet_rejects_global_error_budget(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A global allowance cannot bypass the file/rule ratchet."""

    config = MaintainerConfig(
        diagnostic_artifacts_dir=str(tmp_path),
        pyright_strict_ratchet_enabled=True,
        pyright_strict_max_errors=1,
    )

    assert pyright_strict.run_strict_ratchet(config) == 1
    assert "must be 0" in capsys.readouterr().out


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
    monkeypatch.setattr(pyright_strict.strict_baseline, "load_baseline", zero_baseline)

    assert pyright_strict.run_strict_ratchet(config) == 1


def test_run_pyright_json_reports_invalid_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid Pyright JSON returns no payload."""

    monkeypatch.setattr(pyright_strict.pyright, "pyright_executable", fake_executable)
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

    monkeypatch.setattr(pyright_strict.pyright, "pyright_executable", fake_executable)
    monkeypatch.setattr(
        pyright_strict.subprocess,
        "run",
        failed_pyright_run,
    )

    assert pyright_strict.run_pyright_json(tmp_path / "config.json", tmp_path / "out.json") is None


def test_stats_rejects_summary_diagnostic_mismatch(tmp_path: Path) -> None:
    """The ratchet cannot compare a partial or inconsistent diagnostic list."""

    with pytest.raises(pyright_strict.StrictPayloadError, match="does not match"):
        pyright_strict.stats_from_payload(
            {
                "version": PYRIGHT_VERSION,
                "summary": {"errorCount": 1, "filesAnalyzed": 1},
                "generalDiagnostics": [],
            },
            scope=sample_scope(tmp_path),
        )


@pytest.mark.parametrize(
    "diagnostics",
    ({}, [None], [{"severity": "unexpected"}]),
)
def test_stats_rejects_malformed_diagnostic_collection(
    tmp_path: Path,
    diagnostics: object,
) -> None:
    """Malformed diagnostic collections cannot masquerade as zero errors."""

    with pytest.raises(pyright_strict.StrictPayloadError):
        pyright_strict.stats_from_payload(
            {
                "version": PYRIGHT_VERSION,
                "summary": {"errorCount": 0, "filesAnalyzed": 1},
                "generalDiagnostics": diagnostics,
            },
            scope=sample_scope(tmp_path),
        )


def test_stats_rejects_out_of_scope_diagnostic(tmp_path: Path) -> None:
    """A diagnostic outside the generated include roots fails closed."""

    outside = tmp_path / "other" / "outside.py"
    with pytest.raises(pyright_strict.StrictPayloadError, match="outside strict include scope"):
        pyright_strict.stats_from_payload(
            {
                "version": PYRIGHT_VERSION,
                "summary": {"errorCount": 1, "filesAnalyzed": 1},
                "generalDiagnostics": [
                    {
                        "severity": "error",
                        "file": str(outside),
                        "rule": "reportUnknownMemberType",
                    }
                ],
            },
            scope=sample_scope(tmp_path),
        )


def test_scope_fingerprint_is_output_directory_independent(tmp_path: Path) -> None:
    """Equivalent generated configs keep one normalized scope identity."""

    (tmp_path / "src").mkdir()
    first = tmp_path / "one" / "strict.json"
    second = tmp_path / "nested" / "two" / "strict.json"
    first.parent.mkdir()
    second.parent.mkdir(parents=True)
    write_scope_config(first, include="../src", root="..")
    write_scope_config(second, include="../../src", root="../..")

    first_scope = pyright_strict.scope_from_config(first, repo_root=tmp_path)
    second_scope = pyright_strict.scope_from_config(second, repo_root=tmp_path)

    assert first_scope.sha256 == second_scope.sha256
    assert first_scope.include_roots == second_scope.include_roots


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

    return {
        "version": PYRIGHT_VERSION,
        "summary": {"errorCount": ZERO_ERRORS, "filesAnalyzed": ZERO_ERRORS},
        "generalDiagnostics": [],
    }


def zero_baseline(_path: Path) -> strict_baseline.StrictBaseline:
    """Return empty baseline for runner tests."""

    return strict_baseline.StrictBaseline(
        pyright_version=PYRIGHT_VERSION,
        scope_sha256=SCOPE_SHA256,
        pairs={},
    )


def sample_scope(repo_root: Path) -> pyright_strict.StrictScope:
    """Return an in-repository test scope."""

    root = repo_root.resolve()
    return pyright_strict.StrictScope(
        repo_root=root,
        include_roots=(root / "src", root / "tests"),
        sha256=SCOPE_SHA256,
    )


def fixed_scope(_config_path: Path, *, repo_root: Path) -> pyright_strict.StrictScope:
    """Return a stable scope for runner orchestration tests."""

    return sample_scope(repo_root)


def write_scope_config(path: Path, *, include: str, root: str) -> None:
    """Write one generated-config fixture with normalized equivalent paths."""

    path.write_text(
        json.dumps(
            {
                "include": [include],
                "exclude": [f"{root}/build"],
                "extraPaths": [root, f"{root}/src"],
                "typeCheckingMode": "strict",
                "reportMissingTypeStubs": False,
            }
        ),
        encoding="utf-8",
    )


def fake_executable() -> str:
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

    return {
        "version": PYRIGHT_VERSION,
        "summary": {"errorCount": ZERO_ERRORS, "filesAnalyzed": SAMPLE_FILES},
        "generalDiagnostics": [],
    }


def sample_payload() -> dict[str, object]:
    """Return strict Pyright payload with sample errors."""

    return {
        "version": PYRIGHT_VERSION,
        "summary": {"errorCount": 1, "filesAnalyzed": SAMPLE_FILES},
        "generalDiagnostics": [
            {
                "severity": "error",
                "file": "src/example.py",
                "rule": "reportUnknownMemberType",
            },
        ],
    }
