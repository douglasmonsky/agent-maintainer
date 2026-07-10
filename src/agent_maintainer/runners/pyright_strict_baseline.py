"""Versioned file/rule baseline for strict Pyright diagnostics."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

STRICT_BASELINE_SCHEMA_VERSION = 2
PYRIGHT_TOOL_NAME = "pyright"
STRICT_TYPE_CHECKING_MODE = "strict"
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
TOP_SUMMARY_LIMIT = 10

type PairCounts = dict[str, dict[str, int]]


@dataclass(frozen=True)
class StrictPyrightStats:
    """Canonical strict diagnostics from one Pyright run."""

    files_analyzed: int
    pyright_version: str
    scope_sha256: str
    pairs: PairCounts

    @property
    def total_errors(self) -> int:
        """Return the diagnostic-derived error total."""

        return pair_total(self.pairs)

    @property
    def by_rule(self) -> dict[str, int]:
        """Return review summary grouped by rule."""

        return pair_rule_counts(self.pairs)

    @property
    def by_file(self) -> dict[str, int]:
        """Return review summary grouped by file."""

        return {file: sum(rules.values()) for file, rules in self.pairs.items()}


@dataclass(frozen=True)
class StrictBaseline:
    """Committed strict-Pyright file/rule allowances."""

    pyright_version: str
    scope_sha256: str
    pairs: PairCounts

    @property
    def total_errors(self) -> int:
        """Return the diagnostic-derived baseline total."""

        return pair_total(self.pairs)

    @property
    def by_rule(self) -> dict[str, int]:
        """Return baseline counts grouped by rule."""

        return pair_rule_counts(self.pairs)


@dataclass(frozen=True)
class StrictRegression:
    """One file/rule pair whose allowance increased."""

    file: str
    rule: str
    current_count: int
    baseline_count: int

    def render(self) -> str:
        """Return one compact pair-regression line."""

        delta = self.current_count - self.baseline_count
        delta_text = format(delta, "+d")
        return "".join(
            (
                f"- {self.file} :: ",
                f"{self.rule}: ",
                f"{self.current_count} ",
                f"(baseline {self.baseline_count}, ",
                f"{delta_text})",
            )
        )


@dataclass(frozen=True)
class StrictRatchetResult:
    """Strict-Pyright baseline comparison result."""

    passed: bool
    current: StrictPyrightStats
    baseline: StrictBaseline
    regressions: tuple[StrictRegression, ...]
    compatibility_errors: tuple[str, ...]

    def headline_lines(self) -> tuple[str, str]:
        """Return summary-first result lines."""

        status = "passed" if self.passed else "failed"
        current_errors = self.current.total_errors
        baseline_errors = self.baseline.total_errors
        delta = current_errors - baseline_errors
        delta_text = format(delta, "+d")
        headline = "".join(
            (
                f"pyright strict ratchet {status}: ",
                f"{current_errors} errors ",
                f"(baseline {baseline_errors}, ",
                f"delta {delta_text})",
            )
        )
        files_analyzed = self.current.files_analyzed
        return headline, f"files analyzed: {files_analyzed}"

    def regression_lines(self) -> list[str]:
        """Return regressions ranked by increase, then identity."""

        ranked = sorted(
            self.regressions,
            key=lambda item: (-(item.current_count - item.baseline_count), item.file, item.rule),
        )
        return [item.render() for item in ranked[:TOP_SUMMARY_LIMIT]]


def load_baseline(path: Path) -> StrictBaseline | None:
    """Load a fail-closed v2 strict-Pyright baseline."""

    if not path.exists():
        print(f"pyright strict baseline missing: {path}")
        return None
    try:
        return parse_baseline_payload(read_baseline_payload(path))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"pyright strict baseline invalid: {path}: {exc}")
        return None


def read_baseline_payload(path: Path) -> dict[str, Any]:
    """Read one baseline JSON object."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("top level must be an object")
    return cast(dict[str, Any], raw)


def parse_baseline_payload(payload: dict[str, Any]) -> StrictBaseline:
    """Parse and validate the exact v2 baseline schema."""

    allowed_keys = {"schema_version", "tool", "total_errors", "by_rule", "pairs", "note"}
    unknown_keys = sorted(set(payload) - allowed_keys)
    if unknown_keys:
        unknown_text = ", ".join(unknown_keys)
        raise ValueError(f"unknown keys: {unknown_text}")
    if payload.get("schema_version") != STRICT_BASELINE_SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {STRICT_BASELINE_SCHEMA_VERSION}")
    pyright_version, scope_sha256 = parse_tool_metadata(required_object(payload, "tool"))
    pairs = parse_pairs(required_object(payload, "pairs"))
    validate_summaries(payload, pairs)
    note = payload.get("note", "")
    if not isinstance(note, str):
        raise ValueError("note must be a string")
    return StrictBaseline(
        pyright_version=pyright_version,
        scope_sha256=scope_sha256,
        pairs=pairs,
    )


def parse_tool_metadata(tool: dict[str, Any]) -> tuple[str, str]:
    """Return validated Pyright version and strict-scope digest."""

    expected = {"name", "version", "type_checking_mode", "scope_sha256"}
    issues: list[str] = []
    if set(tool) != expected:
        issues.append("tool must contain only name, version, type_checking_mode, scope_sha256")
    if tool.get("name") != PYRIGHT_TOOL_NAME:
        issues.append(f"tool.name must be {PYRIGHT_TOOL_NAME!r}")
    if tool.get("type_checking_mode") != STRICT_TYPE_CHECKING_MODE:
        issues.append(f"tool.type_checking_mode must be {STRICT_TYPE_CHECKING_MODE!r}")
    pyright_version = required_text(tool, "version", label="tool")
    scope_sha256 = required_text(tool, "scope_sha256", label="tool")
    if SHA256_PATTERN.fullmatch(scope_sha256) is None:
        issues.append("tool.scope_sha256 must be a lowercase SHA-256 digest")
    if issues:
        raise ValueError("; ".join(issues))
    return pyright_version, scope_sha256


def validate_summaries(payload: dict[str, Any], pairs: PairCounts) -> None:
    """Require human-review summaries to match canonical pair counts."""

    expected_total = payload.get("total_errors")
    if (
        isinstance(expected_total, bool)
        or not isinstance(expected_total, int)
        or expected_total < 0
    ):
        raise ValueError("total_errors must be a non-negative integer")
    if expected_total != pair_total(pairs):
        raise ValueError("total_errors does not match pairs")
    by_rule = parse_positive_counts(required_object(payload, "by_rule"), label="by_rule")
    if by_rule != pair_rule_counts(pairs):
        raise ValueError("by_rule does not match pairs")


def parse_pairs(raw: dict[str, Any]) -> PairCounts:
    """Return validated repository-relative file/rule counts."""

    pairs: PairCounts = {}
    for file, value in raw.items():
        path = PurePosixPath(file)
        lexical_invalid = not file or "\\" in file
        structural_invalid = path.is_absolute() or path.as_posix() != file or ".." in path.parts
        invalid_path = lexical_invalid or structural_invalid
        if invalid_path:
            raise ValueError(f"pairs path is not canonical repository-relative: {file!r}")
        if not isinstance(value, dict):
            raise ValueError(f"pairs.{file} must be an object")
        rules = parse_positive_counts(cast(dict[str, Any], value), label=f"pairs.{file}")
        if not rules:
            raise ValueError(f"pairs.{file} must not be empty")
        pairs[file] = rules
    return pairs


def parse_positive_counts(raw: dict[str, Any], *, label: str) -> dict[str, int]:
    """Return non-empty-key positive integer counts."""

    counts: dict[str, int] = {}
    for name, count in raw.items():
        if not name:
            raise ValueError(f"{label} keys must be non-empty strings")
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ValueError(f"{label}.{name} must be a positive integer")
        counts[name] = count
    return counts


def compare_stats(current: StrictPyrightStats, baseline: StrictBaseline) -> StrictRatchetResult:
    """Compare every current file/rule pair to its independent allowance."""

    compatibility_errors = baseline_compatibility_errors(current, baseline)
    regressions = tuple(
        StrictRegression(
            file=file,
            rule=rule,
            current_count=count,
            baseline_count=baseline.pairs.get(file, {}).get(rule, 0),
        )
        for file, rules in sorted(current.pairs.items())
        for rule, count in sorted(rules.items())
        if count > baseline.pairs.get(file, {}).get(rule, 0)
    )
    return StrictRatchetResult(
        passed=not compatibility_errors and not regressions,
        current=current,
        baseline=baseline,
        regressions=regressions,
        compatibility_errors=compatibility_errors,
    )


def baseline_compatibility_errors(
    current: StrictPyrightStats,
    baseline: StrictBaseline,
) -> tuple[str, ...]:
    """Return tool/scope changes that require explicit baseline migration."""

    errors: list[str] = []
    if current.pyright_version != baseline.pyright_version:
        version_change = f"{baseline.pyright_version} -> {current.pyright_version}"
        errors.append(f"Pyright version changed ({version_change}); review a new baseline.")
    if current.scope_sha256 != baseline.scope_sha256:
        errors.append("strict analysis scope changed; review a new baseline.")
    return tuple(errors)


def baseline_json(current: StrictPyrightStats, *, note: str = "") -> str:
    """Return deterministic v2 candidate JSON for intentional review."""

    payload: dict[str, object] = {
        "schema_version": STRICT_BASELINE_SCHEMA_VERSION,
        "tool": {
            "name": PYRIGHT_TOOL_NAME,
            "version": current.pyright_version,
            "type_checking_mode": STRICT_TYPE_CHECKING_MODE,
            "scope_sha256": current.scope_sha256,
        },
        "total_errors": current.total_errors,
        "by_rule": current.by_rule,
        "pairs": current.pairs,
        "note": note,
    }
    return f"{json.dumps(payload, indent=2, sort_keys=True)}\n"


def format_result(result: StrictRatchetResult) -> str:
    """Format a compact, pair-aware ratchet result."""

    lines = list(result.headline_lines())
    if result.compatibility_errors:
        compatibility_lines = [f"- {item}" for item in result.compatibility_errors]
        lines.extend(("baseline compatibility:", *compatibility_lines[:TOP_SUMMARY_LIMIT]))
    if result.regressions:
        lines.extend(("regressed file/rule pairs:", *result.regression_lines()))
    lines.extend(
        (
            "top rules:",
            *format_top_counts(result.current.by_rule),
            "top files:",
            *format_top_counts(result.current.by_file),
        )
    )
    if not result.passed:
        lines.append("Repair: reduce the named pair or intentionally review a new v2 baseline.")
    return "\n".join(lines)


def pair_total(pairs: PairCounts) -> int:
    """Return total pair counts."""

    return sum(count for rules in pairs.values() for count in rules.values())


def pair_rule_counts(pairs: PairCounts) -> dict[str, int]:
    """Return pair counts grouped by rule."""

    counts: Counter[str] = Counter()
    for rules in pairs.values():
        counts.update(rules)
    return dict(counts)


def required_object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    """Return one required JSON object."""

    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return cast(dict[str, Any], value)


def required_text(payload: dict[str, Any], key: str, *, label: str) -> str:
    """Return one required non-empty string."""

    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label}.{key} must be a non-empty string")
    return value


def format_top_counts(counts: dict[str, int]) -> list[str]:
    """Return compact top-count lines."""

    if not counts:
        return ["- none"]
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [f"- {name}: {count}" for name, count in ranked[:TOP_SUMMARY_LIMIT]]
