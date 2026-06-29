"""Changed source discovery for test intelligence."""

from __future__ import annotations

from agent_maintainer.checks.change_budget import (
    changed_python_files,
    run_git_numstat,
)
from agent_maintainer.config.schema import MaintainerConfig


def changed_source_paths(
    config: MaintainerConfig,
    *,
    base_ref: str,
    staged: bool,
) -> tuple[str, ...]:
    """Return changed Python source files for configured roots."""

    changes = run_git_numstat(base_ref, staged=staged)
    source_changes, _test_changes = changed_python_files(changes, config)
    return tuple(sorted(change.path for change in source_changes))
