"""Render exported Mutmut result statistics."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.runners.mutmut_stats import MutmutStats, render_summary
from agent_maintainer.runners.mutmut_stats import read_stats as read_mutmut_stats


def read_stats(path: Path) -> MutmutStats:
    """Read exported Mutmut result statistics."""

    return read_mutmut_stats(path)


def render_json(stats: MutmutStats) -> str:
    """Render mutation result stats as JSON."""

    return json.dumps(
        {
            "killed": stats.killed,
            "survived": stats.survived,
            "total": stats.total,
            "no_tests": stats.no_tests,
            "skipped": stats.skipped,
            "suspicious": stats.suspicious,
            "timeout": stats.timeout,
            "check_was_interrupted_by_user": stats.check_was_interrupted_by_user,
            "segfault": stats.segfault,
            "score": stats.score,
        },
        indent=2,
        sort_keys=True,
    )


def render_text(stats: MutmutStats) -> str:
    """Render mutation result stats as compact text."""

    return render_summary(stats)
