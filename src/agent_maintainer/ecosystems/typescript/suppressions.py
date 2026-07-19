"""TypeScript and JavaScript suppression classification."""

from __future__ import annotations

import re

from agent_maintainer.ecosystems.models import SuppressionFinding

ECOSYSTEM_NAME = "typescript"

ESLINT_DISABLE_RE = re.compile(r"//\s*eslint-disable(?:-next-line|-line)?(?:\s|$)")
ESLINT_BLOCK_DISABLE_RE = re.compile(r"/\*\s*eslint-disable(?:\s|\*/|$)")
ESLINT_RULE_RE = re.compile(r"eslint-disable(?:-next-line|-line)?\s+[\w@/-]")
TS_IGNORE_RE = re.compile(r"//\s*@ts-ignore\b")
TS_EXPECT_ERROR_RE = re.compile(r"//\s*@ts-expect-error\b")
TS_NOCHECK_RE = re.compile(r"//\s*@ts-nocheck\b")
ISTANBUL_IGNORE_RE = re.compile(r"(?:/\*|//)\s*istanbul ignore")
C8_IGNORE_RE = re.compile(r"(?:/\*|//)\s*c8 ignore")


def classify_line(line: str, path: str = "") -> tuple[SuppressionFinding, ...]:
    """Return TypeScript/JavaScript suppression findings in one source line."""
    del path
    findings: list[SuppressionFinding] = []
    if ESLINT_DISABLE_RE.search(line) or ESLINT_BLOCK_DISABLE_RE.search(line):
        findings.append(_eslint_finding(line))
    if TS_IGNORE_RE.search(line):
        findings.append(
            _finding(
                "ts-ignore",
                line,
                broad=True,
                reason="TypeScript ignore suppresses the next diagnostic.",
            ),
        )
    if TS_EXPECT_ERROR_RE.search(line):
        findings.append(
            _finding(
                "ts-expect-error",
                line,
                broad=False,
                reason="TypeScript expected error should be justified.",
            ),
        )
    if TS_NOCHECK_RE.search(line):
        findings.append(
            _finding(
                "ts-nocheck",
                line,
                broad=True,
                reason="TypeScript no-check disables diagnostics for a file.",
            ),
        )
    if ISTANBUL_IGNORE_RE.search(line):
        findings.append(
            _finding(
                "istanbul-ignore",
                line,
                broad=False,
                reason="Coverage ignore marker.",
            ),
        )
    if C8_IGNORE_RE.search(line):
        findings.append(
            _finding(
                "c8-ignore",
                line,
                broad=False,
                reason="Coverage ignore marker.",
            ),
        )
    return tuple(findings)


def _eslint_finding(line: str) -> SuppressionFinding:
    """Return ESLint suppression finding broadness classification."""
    has_rule = ESLINT_RULE_RE.search(line) is not None
    if has_rule:
        reason = "ESLint disable names a specific rule."
        is_broad = False
    else:
        reason = "ESLint disable lacks a specific rule."
        is_broad = True
    return _finding(
        "eslint-disable",
        line,
        broad=is_broad,
        reason=reason,
    )


def _finding(
    kind: str,
    line: str,
    *,
    broad: bool,
    reason: str,
) -> SuppressionFinding:
    """Build one TypeScript/JavaScript suppression finding."""
    return SuppressionFinding(
        ecosystem=ECOSYSTEM_NAME,
        kind=kind,
        line=line,
        broad=broad,
        reason=reason,
    )
