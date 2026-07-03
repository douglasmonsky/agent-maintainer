"""Tests Technical Debt Score assessment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.assess import cli
from agent_maintainer.assess.debt_score import (
    DEBT_SCORE_JSON,
    DEBT_SCORE_MARKDOWN,
    _summary,
    build_debt_report,
    score_interpretation,
)
from agent_maintainer.assess.evidence import collect_evidence
from agent_maintainer.assess.models import DebtCategory, DebtScoreReport
from agent_maintainer.config.schema import MaintainerConfig

MANY_SOURCE_FILES = 45
HIGH_CATEGORY_SCORE = 50
MODERATE_CATEGORY_SCORE = 40
STRICT_CHANGE_FILES = 30
STRICT_CHANGE_LINES = 1_000
LOW_COVERAGE_FLOOR = 50
LONG_SOURCE_LIMIT = 500
HIGH_COMPLEXITY = 20
HEALTHY_MUTATION_SCORE = 5
EXCELLENT_DEBT_SCORE = 10
CRITICAL_SCORE_SAMPLE = 90
LOW_RISK_CATEGORY_SCORE = 25


def test_debt_score_cli_writes_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Debt score command writes JSON and Markdown artifacts by default."""
    write_repo(tmp_path)

    status = cli.main(["debt", "--target", str(tmp_path), "--json"])

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["score"] >= 0
    assert payload["risk"] in {"low", "moderate", "high", "critical"}
    assert payload["interpretation"]
    assert {category["name"] for category in payload["categories"]} >= {
        "Reviewability",
        "Tests and Coverage",
        "Architecture Boundaries",
    }
    assert all("interpretation" in category for category in payload["categories"])
    assert (tmp_path / ".verify-logs" / DEBT_SCORE_JSON).exists()
    assert (tmp_path / ".verify-logs" / DEBT_SCORE_MARKDOWN).exists()
    markdown = (tmp_path / ".verify-logs" / DEBT_SCORE_MARKDOWN).read_text(
        encoding="utf-8",
    )
    assert "tolerance signals" in markdown
    assert "Interpretation:" in markdown


def test_debt_score_no_write_skips_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Debt score can render without writing diagnostics."""
    write_repo(tmp_path)

    status = cli.main(["debt", "--target", str(tmp_path), "--no-write"])

    assert status == 0
    assert "Technical Debt Score" in capsys.readouterr().out
    assert not (tmp_path / ".verify-logs" / DEBT_SCORE_JSON).exists()


def test_debt_score_penalizes_missing_controls(tmp_path: Path) -> None:
    """Weak repo evidence raises the relevant category scores."""

    write_repo(tmp_path)
    (tmp_path / "tests" / "test_example.py").unlink()
    (tmp_path / "tests").rmdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / "requirements.txt").write_text("example==1\n", encoding="utf-8")
    package = tmp_path / "src" / "example"
    for index in range(MANY_SOURCE_FILES):
        (package / f"module_{index}.py").write_text("VALUE = 1\n", encoding="utf-8")

    config = MaintainerConfig(
        architecture_tool="tach",
        change_block_files=STRICT_CHANGE_FILES,
        change_block_lines=STRICT_CHANGE_LINES,
        coverage_fail_under=LOW_COVERAGE_FLOOR,
        diagnostic_artifacts_enabled=False,
        enable_wemake=False,
        file_length_max_source=LONG_SOURCE_LIMIT,
        mode="fresh-strict",
        pyright_type_checking_mode="basic",
        require_tests=False,
        ruff_max_complexity=HIGH_COMPLEXITY,
    )

    report = build_debt_report(
        collect_evidence(tmp_path),
        config,
        log_dir=tmp_path / ".verify-logs",
    )
    categories = {category.name: category for category in report.categories}

    assert categories["Reviewability"].score >= HIGH_CATEGORY_SCORE
    assert categories["Tests and Coverage"].score > HIGH_CATEGORY_SCORE
    assert categories["Type and Style"].score > MODERATE_CATEGORY_SCORE
    assert categories["Architecture Boundaries"].score > LOW_RISK_CATEGORY_SCORE
    assert categories["Dependencies and Security"].score > MODERATE_CATEGORY_SCORE
    assert categories["Diagnostics Repair Loop"].score > LOW_RISK_CATEGORY_SCORE


# docsync:evidence.start evidence.technical_debt.score_tests
def test_debt_score_rewards_mutation_ratchets_and_manifest(tmp_path: Path) -> None:
    """Healthy ratchet evidence lowers mutation debt and raises confidence."""

    write_repo(tmp_path)
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    (log_dir / "manifest.json").write_text("{}", encoding="utf-8")
    config = MaintainerConfig(
        enable_mutmut=True,
        mutmut_result_ratchet_enabled=True,
        mutmut_target_min=3,
        ratchet_enabled=True,
    )

    report = build_debt_report(collect_evidence(tmp_path), config, log_dir=log_dir)
    categories = {category.name: category for category in report.categories}

    assert report.confidence == "high"
    assert categories["Ratchets and Mutation Maturity"].score == HEALTHY_MUTATION_SCORE


def test_debt_score_allows_excellent_repos_below_ten(tmp_path: Path) -> None:
    """Excellent active controls can produce an excellent advisory score."""

    write_repo(tmp_path)
    (tmp_path / "AGENTS.agent-maintainer.md").write_text("generated\n", encoding="utf-8")
    (tmp_path / "tach.toml").write_text(
        'source_roots = ["src"]\nroot_module = "forbid"\n',
        encoding="utf-8",
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "dev-lock.txt").write_text("example==1\n", encoding="utf-8")
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    (log_dir / "manifest.json").write_text(
        json.dumps({"checks": [{"name": "pyright", "status": "passed"}]}),
        encoding="utf-8",
    )
    config = MaintainerConfig(
        architecture_tool="tach",
        coverage_fail_under=90,
        diff_cover_fail_under=90,
        enable_interrogate=True,
        enable_license_check=True,
        enable_markdownlint=True,
        enable_mutmut=True,
        enable_pip_audit=True,
        enable_sbom=True,
        enable_secret_scanning=True,
        enable_taplo=True,
        enable_wemake=True,
        file_length_max_source=375,
        mutmut_result_ratchet_enabled=True,
        mutmut_target_min=3,
        pyright_strict_ratchet_enabled=True,
        ruff_max_complexity=8,
    )

    report = build_debt_report(collect_evidence(tmp_path), config, log_dir=log_dir)

    assert report.score < EXCELLENT_DEBT_SCORE


# docsync:evidence.end evidence.technical_debt.score_tests


def test_debt_score_penalizes_failed_manifest_check(tmp_path: Path) -> None:
    """Latest verifier failures calibrate category-level debt."""
    write_repo(tmp_path)
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    (log_dir / "manifest.json").write_text(
        json.dumps({"checks": [{"name": "pyright", "status": "failed"}]}),
        encoding="utf-8",
    )

    report = build_debt_report(collect_evidence(tmp_path), MaintainerConfig(), log_dir=log_dir)
    category = _category(report, "Type and Style")

    assert category.score > LOW_RISK_CATEGORY_SCORE
    assert "manifest failed checks = pyright" in category.evidence


def test_debt_score_does_not_penalize_absent_security_surface(tmp_path: Path) -> None:
    """Optional security gates do not count as debt without relevant evidence."""
    report = build_debt_report(
        collect_evidence(tmp_path),
        MaintainerConfig(),
        log_dir=tmp_path / ".verify-logs",
    )
    category = _category(report, "Dependencies and Security")

    assert category.score <= LOW_RISK_CATEGORY_SCORE
    assert any("no dependency" in item for item in category.evidence)
    assert any("lock file present" in item for item in category.evidence)


def test_debt_score_truncated_scan_lowers_confidence(tmp_path: Path) -> None:
    """Truncated evidence scans keep debt scoring low-confidence."""
    write_repo(tmp_path)

    report = build_debt_report(
        collect_evidence(tmp_path, max_files=1),
        MaintainerConfig(),
        log_dir=tmp_path / ".verify-logs",
    )

    assert report.confidence == "low"


def test_debt_score_summary_bands() -> None:
    """Score summaries cover each risk band."""

    assert "strong maintenance controls" in _summary(10)
    assert "watch items" in score_interpretation(10)
    assert "few adoption gaps" in _summary(40)
    assert "meaningful debt risk" in _summary(60)
    assert "conservative ratchets" in _summary(CRITICAL_SCORE_SAMPLE)


def _category(report: DebtScoreReport, name: str) -> DebtCategory:
    """Return category by name from a debt report."""
    return next(category for category in report.categories if category.name == name)


def write_repo(root: Path) -> None:
    """Write a minimal Python repo fixture."""
    (root / "pyproject.toml").write_text(
        """
[tool.agent_maintainer]
mode = "custom"
require_tests = true
coverage_fail_under = 85
diagnostic_artifacts_enabled = true
""".strip(),
        encoding="utf-8",
    )
    package = root / "src" / "example"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_example.py").write_text(
        "def test_example():\n    assert True\n",
        encoding="utf-8",
    )
