"""Structured models for test intelligence output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TestMatch:
    """One likely test file for a changed source file."""

    __test__: ClassVar[bool] = False

    source_path: str
    test_path: str
    confidence: str
    reasons: tuple[str, ...]

    @property
    def pytest_command(self) -> str:
        """Return focused pytest command for this test file."""

        return f"python -m pytest {self.test_path} -q"

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "source_path": self.source_path,
            "test_path": self.test_path,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "pytest_command": self.pytest_command,
        }


@dataclass(frozen=True)
class CoverageSummary:
    """Coverage information for changed source."""

    changed_source_file_coverage: float | None = None
    changed_line_coverage: float | None = None
    branch_coverage_gaps: int | None = None

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "changed_source_file_coverage": self.changed_source_file_coverage,
            "changed_line_coverage": self.changed_line_coverage,
            "branch_coverage_gaps": self.branch_coverage_gaps,
        }


@dataclass(frozen=True)
class TestIntelReport:
    """Test intelligence report for one changed diff."""

    __test__: ClassVar[bool] = False

    changed_source: tuple[str, ...]
    likely_tests: tuple[TestMatch, ...]
    coverage: CoverageSummary
    suggested_actions: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "changed_source": list(self.changed_source),
            "likely_tests": [match.to_json() for match in self.likely_tests],
            "coverage": self.coverage.to_json(),
            "suggested_actions": list(self.suggested_actions),
        }
