"""Upward-only JaCoCo Gradle property thresholds and exact XML headroom."""

from __future__ import annotations

import re
import subprocess  # nosec B404 - fixed local Git read commands only
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal, InvalidOperation
from pathlib import Path, PurePosixPath

from agent_maintainer.ecosystems.java.errors import JavaConfigurationError
from agent_maintainer.ecosystems.java.reports.jacoco import JacocoCoverage

DEFAULT_LINE_THRESHOLD = Decimal("0.80")
DEFAULT_BRANCH_THRESHOLD = Decimal("0.70")
RATIO_QUANTUM = Decimal("0.01")
PERCENT_QUANTUM = Decimal("0.0001")
PERCENT_MULTIPLIER = Decimal(100)
THRESHOLD_VALUE = re.compile(r"(?:0(?:\.\d{1,4})?|1(?:\.0{1,4})?)")


class JacocoThresholdError(JavaConfigurationError, ValueError):
    """Invalid, unavailable, or regressed JaCoCo threshold evidence."""


@dataclass(frozen=True)
class JacocoThresholds:
    """Line and branch Gradle verification ratios."""

    line: Decimal
    branch: Decimal

    def __post_init__(self) -> None:
        _validate_ratio(self.line, "line")
        _validate_ratio(self.branch, "branch")


@dataclass(frozen=True)
class JacocoPropertyNames:
    """Configured Gradle property names for line and branch thresholds."""

    line: str
    branch: str

    def __post_init__(self) -> None:
        if not self.line.strip() or not self.branch.strip() or self.line == self.branch:
            raise JacocoThresholdError("JaCoCo property names must be distinct and non-empty")


@dataclass(frozen=True)
class JacocoThresholdReport:
    """Upward-only property comparison plus separately reported XML headroom."""

    current: JacocoThresholds
    base: JacocoThresholds
    line_headroom: Decimal
    branch_headroom: Decimal
    regressions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        """Return whether neither configured threshold decreased."""
        return not self.regressions


def default_thresholds() -> JacocoThresholds:
    """Return strict defaults for a newly scaffolded repository."""
    return JacocoThresholds(DEFAULT_LINE_THRESHOLD, DEFAULT_BRANCH_THRESHOLD)


def established_thresholds(coverage: JacocoCoverage) -> JacocoThresholds:
    """Round successfully observed coverage down to whole percentage floors."""
    return JacocoThresholds(
        _established_ratio(coverage.line.percentage),
        _established_ratio(coverage.branch.percentage),
    )


def read_current_thresholds(
    workspace: Path,
    *,
    gradle_root: Path,
    properties: JacocoPropertyNames,
) -> JacocoThresholds:
    """Read required configured thresholds from current gradle.properties."""
    properties_path = _current_properties_path(workspace, gradle_root)
    try:
        text = properties_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise JacocoThresholdError("current Gradle coverage properties are unavailable") from exc
    return parse_thresholds(text, properties)


def evaluate_thresholds(
    workspace: Path,
    *,
    gradle_root: Path,
    base_ref: str,
    properties: JacocoPropertyNames,
    coverage: JacocoCoverage,
) -> JacocoThresholdReport:
    """Compare current/base properties and report XML headroom independently."""
    current = read_current_thresholds(
        workspace,
        gradle_root=gradle_root,
        properties=properties,
    )
    base = _read_base_thresholds(
        workspace,
        gradle_root,
        base_ref,
        properties,
    )
    regressions = tuple(
        name for name in ("line", "branch") if getattr(current, name) < getattr(base, name)
    )
    return JacocoThresholdReport(
        current=current,
        base=base,
        line_headroom=_headroom(coverage.line.percentage, current.line),
        branch_headroom=_headroom(coverage.branch.percentage, current.branch),
        regressions=regressions,
    )


def _read_base_thresholds(
    workspace: Path,
    gradle_root: Path,
    base_ref: str,
    properties: JacocoPropertyNames,
) -> JacocoThresholds:
    if not base_ref or base_ref.startswith("-") or ":" in base_ref or "\n" in base_ref:
        raise JacocoThresholdError("JaCoCo base reference is invalid")
    relative_path = _base_properties_path(workspace, gradle_root)
    completed = _run_git(workspace, "show", f"{base_ref}:{relative_path.as_posix()}")
    if completed.returncode != 0:
        raise JacocoThresholdError("base Gradle coverage properties are unavailable")
    return parse_thresholds(completed.stdout, properties)


def _current_properties_path(workspace: Path, gradle_root: Path) -> Path:
    root = workspace.resolve(strict=True)
    candidate = (root / gradle_root / "gradle.properties").resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise JacocoThresholdError("Gradle coverage properties escape the repository") from exc
    return candidate


def _base_properties_path(workspace: Path, gradle_root: Path) -> PurePosixPath:
    current = _current_properties_path(workspace, gradle_root)
    git_root = _git_root(workspace)
    try:
        relative = current.relative_to(git_root)
    except ValueError as exc:
        raise JacocoThresholdError("Gradle coverage properties escape the repository") from exc
    return PurePosixPath(relative.as_posix())


def _git_root(workspace: Path) -> Path:
    completed = _run_git(workspace, "rev-parse", "--show-toplevel")
    if completed.returncode != 0 or not completed.stdout.strip():
        raise JacocoThresholdError("Git repository root is unavailable")
    try:
        return Path(completed.stdout.strip()).resolve(strict=True)
    except OSError as exc:
        raise JacocoThresholdError("Git repository root is unavailable") from exc


def parse_thresholds(
    text: str,
    properties: JacocoPropertyNames,
) -> JacocoThresholds:
    """Parse required configured ratios from Gradle properties text."""
    values = _properties(text)
    return JacocoThresholds(
        _required_ratio(values, properties.line),
        _required_ratio(values, properties.branch),
    )


def _properties(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "!")):
            continue
        if "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", maxsplit=1))
        if key in values:
            raise JacocoThresholdError(f"duplicate Gradle property: {key}")
        values[key] = value
    return values


def _required_ratio(values: dict[str, str], property_name: str) -> Decimal:
    raw = values.get(property_name)
    if raw is None:
        raise JacocoThresholdError(f"required Gradle coverage property is missing: {property_name}")
    if THRESHOLD_VALUE.fullmatch(raw) is None:
        raise JacocoThresholdError(f"invalid Gradle coverage property: {property_name}")
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise JacocoThresholdError(f"invalid Gradle coverage property: {property_name}") from exc


def _validate_ratio(value: Decimal, label: str) -> None:
    if not value.is_finite() or value < 0 or value > 1:
        raise JacocoThresholdError(f"JaCoCo {label} threshold must be between zero and one")


def _established_ratio(percentage: Decimal) -> Decimal:
    whole_percent = percentage.to_integral_value(rounding=ROUND_FLOOR)
    return (whole_percent / PERCENT_MULTIPLIER).quantize(RATIO_QUANTUM)


def _headroom(percentage: Decimal, threshold: Decimal) -> Decimal:
    return (percentage - threshold * PERCENT_MULTIPLIER).quantize(PERCENT_QUANTUM)


def _run_git(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # nosec B603
            ("git", "-C", str(workspace), *args),
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
    except OSError as exc:
        raise JacocoThresholdError(f"could not read base Gradle properties: {exc}") from exc
