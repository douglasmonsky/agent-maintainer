"""Worktree planning helpers for the task broker incubator."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorktreePlan:
    """Suggested Git worktree for one task."""

    task_id: str
    path: Path
    branch: str
    base: str
    command: tuple[str, ...]

    def payload(self, root: Path) -> dict[str, object]:
        """Return JSON-serializable plan payload."""
        return {
            "task_id": self.task_id,
            "path": str(self.path),
            "branch": self.branch,
            "base": self.base,
            "command": list(self.command_for(root)),
        }

    def command_for(self, root: Path) -> tuple[str, ...]:
        """Return git worktree command for root."""
        return (
            "git",
            "-C",
            str(root),
            "worktree",
            "add",
            "-b",
            self.branch,
            str(self.path),
            self.base,
        )


def build_worktree_plan(
    root: Path,
    task_id: str,
    *,
    path: Path | None = None,
    branch: str | None = None,
    base: str = "HEAD",
) -> WorktreePlan:
    """Return a deterministic worktree plan for task."""
    resolved_root = root.resolve()
    plan_path = path or resolved_root.parent / f"{resolved_root.name}-{task_id}"
    plan_branch = branch or f"task/{task_id}"
    return WorktreePlan(
        task_id=task_id,
        path=plan_path,
        branch=plan_branch,
        base=base,
        command=(),
    )


def render_worktree_plan(plan: WorktreePlan, root: Path, *, output_format: str) -> str:
    """Render worktree plan as Markdown or JSON."""
    payload = plan.payload(root)
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True)
    if output_format == "markdown":
        command = " ".join(payload["command"])
        return (
            f"# Worktree Plan: {payload['task_id']}\n\n"
            f"- Path: `{payload['path']}`\n"
            f"- Branch: `{payload['branch']}`\n"
            f"- Base: `{payload['base']}`\n\n"
            "## Command\n\n"
            f"```bash\n{command}\n```"
        )
    raise ValueError(f"unknown worktree plan format: {output_format}")


def create_worktree(plan: WorktreePlan, root: Path) -> subprocess.CompletedProcess[str]:
    """Create a Git worktree for plan."""
    plan.path.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        plan.command_for(root),
        check=False,
        text=True,
        capture_output=True,
    )
