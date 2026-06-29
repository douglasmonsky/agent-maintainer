"""Build bounded context for agent-client hook failures."""

from __future__ import annotations

import subprocess  # nosec B404
from contextlib import suppress
from pathlib import Path

from agent_maintainer.config import loader
from agent_maintainer.context import pack_rendering
from agent_maintainer.context import packs as context_packs
from agent_maintainer.context.budget import bound_single_item_text


def hook_config(repo_root: Path) -> loader.schema.MaintainerConfig:
    """Return hook-relevant config with environment overrides."""

    config = loader.apply_pyproject(
        loader.schema.MaintainerConfig(),
        loader.read_pyproject(repo_root / "pyproject.toml"),
    )
    return loader.apply_env(config)


def failure_context(
    repo_root: Path,
    result: subprocess.CompletedProcess[str],
    config: loader.schema.MaintainerConfig,
    limit: int,
) -> str:
    """Return compact bounded hook failure context."""

    raw_output = failure_output(result)
    try:
        pack = write_hook_context_pack(repo_root, config)
    except (OSError, ValueError) as exc:
        return truncate_output(f"{raw_output}\n\nContext pack generation failed: {exc}", limit)
    return truncate_output(
        pack_rendering.render_pack_pointer(
            pack.payload,
            display_path=display_path(pack.markdown_path, repo_root),
        ),
        limit,
    )


def write_hook_context_pack(
    repo_root: Path,
    config: loader.schema.MaintainerConfig,
) -> context_packs.ContextPack:
    """Write context pack for a hook failure."""

    return context_packs.write_context_pack(
        context_packs.ContextPackRequest(
            log_dir=repo_root / ".verify-logs",
            budget=config.context_pack_budget_chars,
            base_ref="HEAD",
            baseline_path=repo_root / config.ratchet_baseline_path,
            failure_limit=config.context_max_failure_items,
            target_limit=config.ratchet_target_limit,
        ),
    )


def failure_output(result: subprocess.CompletedProcess[str]) -> str:
    """Return verifier failure output fallback."""

    return (result.stdout or result.stderr or "Verification failed with no output.").strip()


def display_path(path: Path, repo_root: Path) -> str:
    """Return path relative to repo root when possible."""

    with suppress(ValueError):
        return str(path.relative_to(repo_root))
    return str(path)


def truncate_output(output: str, limit: int) -> str:
    """Return bounded hook output with log-location hint."""

    bounded = bound_single_item_text(output, limit)
    if not bounded.truncated:
        return bounded.text
    return "\n".join(
        (
            bounded.text.rstrip(),
            (
                "... hook output omitted "
                f"{bounded.omitted_chars} chars and {bounded.omitted_lines} lines. "
                "Full logs are in .verify-logs/."
            ),
        ),
    )
