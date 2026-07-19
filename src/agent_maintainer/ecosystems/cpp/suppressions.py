"""C/C++ suppression classification."""

from __future__ import annotations

import re
from pathlib import PurePath

from agent_maintainer.ecosystems.models import SuppressionFinding

ECOSYSTEM_NAME = "cpp"
CPPCHECK_SUPPRESSION_FILE_NAMES = frozenset((".cppcheck-suppressions", "cppcheck-suppressions.txt"))

NOLINT_RE = re.compile(r"\bNOLINT(?:\((?P<rules>[^)]*)\))?(?![\w(])")
NOLINTNEXTLINE_RE = re.compile(r"\bNOLINTNEXTLINE(?:\((?P<rules>[^)]*)\))?(?![\w(])")
NOLINTBEGIN_RE = re.compile(r"\bNOLINTBEGIN(?:\((?P<rules>[^)]*)\))?(?![\w(])")
NOLINTEND_RE = re.compile(r"\bNOLINTEND(?:\((?P<rules>[^)]*)\))?(?![\w(])")
CPPCHECK_SUPPRESS_RE = re.compile(r"\bcppcheck-suppress(?:[ \t]+(?P<rule>[^\s*/]+))?(?=$|\s)")
CPPCHECK_SUPPRESS_FILE_RE = re.compile(r"\bcppcheck-suppress-file(?=$|\s)")

_MARKER_PATTERNS = (
    ("nolint", NOLINT_RE),
    ("nolint-next-line", NOLINTNEXTLINE_RE),
    ("nolint-begin", NOLINTBEGIN_RE),
    ("nolint-end", NOLINTEND_RE),
    ("cppcheck-suppress", CPPCHECK_SUPPRESS_RE),
    ("cppcheck-suppress-file", CPPCHECK_SUPPRESS_FILE_RE),
)


def classify_line(line: str, path: str = "") -> tuple[SuppressionFinding, ...]:
    """Return C/C++ suppression findings in deterministic source order."""
    matches = tuple(
        (match.start(), order, kind, match)
        for order, (kind, pattern) in enumerate(_MARKER_PATTERNS)
        if (match := pattern.search(line)) is not None
    )
    findings = [_marker_finding(kind, line, match) for _, _, kind, match in sorted(matches)]
    if _is_suppression_file_entry(line, path):
        findings.append(
            _finding(
                "cppcheck-suppression-file",
                line,
                broad=False,
                reason="Cppcheck suppression file entry names a diagnostic.",
            )
        )
    return tuple(findings)


def _marker_finding(
    kind: str,
    line: str,
    match: re.Match[str],
) -> SuppressionFinding:
    """Build one marker finding with rule-list broadness."""
    if kind.startswith("nolint"):
        has_rule = bool((match.groupdict().get("rules") or "").strip())
        return _finding(
            kind,
            line,
            broad=not has_rule,
            reason=(
                "NOLINT marker names a rule." if has_rule else "NOLINT marker lacks a rule list."
            ),
        )
    if kind == "cppcheck-suppress":
        has_rule = bool(match.group("rule"))
        return _finding(
            kind,
            line,
            broad=not has_rule,
            reason=(
                "Cppcheck suppression names a diagnostic."
                if has_rule
                else "Cppcheck suppression lacks a diagnostic identifier."
            ),
        )
    return _finding(
        kind,
        line,
        broad=True,
        reason="Cppcheck file suppression applies broadly.",
    )


def _is_suppression_file_entry(line: str, path: str) -> bool:
    """Return whether line is an entry in a recognized cppcheck file."""
    stripped = line.strip()
    return bool(
        path
        and PurePath(path).name in CPPCHECK_SUPPRESSION_FILE_NAMES
        and stripped
        and not stripped.startswith(("#", "//"))
    )


def _finding(
    kind: str,
    line: str,
    *,
    broad: bool,
    reason: str,
) -> SuppressionFinding:
    """Build one C/C++ suppression finding."""
    return SuppressionFinding(
        ecosystem=ECOSYSTEM_NAME,
        kind=kind,
        line=line,
        broad=broad,
        reason=reason,
    )
