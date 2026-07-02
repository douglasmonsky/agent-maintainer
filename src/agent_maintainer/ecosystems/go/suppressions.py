"""Go suppression classification."""

from __future__ import annotations

import re

from agent_maintainer.ecosystems.models import SuppressionFinding

ECOSYSTEM_NAME = "go"
NOLINT_RE = re.compile(r"//\s*nolint(?::(?P<linters>[\w,.-]+))?")


def classify_line(line: str) -> tuple[SuppressionFinding, ...]:
    """Return Go suppression findings in one source line."""
    match = NOLINT_RE.search(line)
    if match is None:
        return ()
    linters = match.group("linters")
    return (
        SuppressionFinding(
            ecosystem=ECOSYSTEM_NAME,
            kind="nolint",
            line=line,
            broad=linters is None,
            reason=(
                "//nolint lacks specific linter names."
                if linters is None
                else "//nolint names specific linters."
            ),
        ),
    )
