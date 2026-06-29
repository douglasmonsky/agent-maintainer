"""Ratchet baseline persistence and provenance."""

from __future__ import annotations

import json
import subprocess  # nosec B404
from datetime import UTC, datetime
from pathlib import Path

from agent_maintainer.core.config import MaintainerConfig, load_config
from agent_maintainer.ratchet.findings import DEFAULT_CHECKS, current_findings
from agent_maintainer.ratchet.models import (
    BaselineProvenance,
    RatchetBaseline,
)

BASELINE_VERSION = 1
CREATED_BY = "agent-maintainer"


def create_baseline(
    *,
    base_ref: str,
    notes: str = "",
    checks: tuple[str, ...] = DEFAULT_CHECKS,
    config: MaintainerConfig | None = None,
) -> RatchetBaseline:
    """Create a baseline from current findings."""

    active_config = config or load_config()
    return RatchetBaseline(
        provenance=BaselineProvenance(
            version=BASELINE_VERSION,
            created_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
            created_by=CREATED_BY,
            base_ref=base_ref,
            repo_commit=git_output("rev-parse", "HEAD"),
            dirty_state=git_dirty(),
            mode=active_config.mode,
            checks=checks,
            notes=notes,
        ),
        findings=current_findings(checks, active_config),
    )


def read_baseline(path: Path) -> RatchetBaseline:
    """Read a ratchet baseline from disk."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return RatchetBaseline.from_dict(payload)


def write_baseline(path: Path, baseline: RatchetBaseline, *, force: bool) -> None:
    """Write a ratchet baseline, refusing overwrite unless requested."""

    if path.exists() and not force:
        raise FileExistsError(f"baseline already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(baseline.to_dict(), indent=2, sort_keys=True)
    path.write_text(f"{payload}\n", encoding="utf-8")


def default_baseline_path(config: MaintainerConfig | None = None) -> Path:
    """Return configured ratchet baseline path."""

    active_config = config or load_config()
    return Path(active_config.ratchet_baseline_path)


def git_dirty() -> bool:
    """Return whether Git reports uncommitted changes."""

    return bool(git_output("status", "--porcelain"))


def git_output(*args: str) -> str:
    """Return stripped Git output or an unknown marker."""

    try:
        result = subprocess.run(  # nosec B603
            ("git", *args),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"
