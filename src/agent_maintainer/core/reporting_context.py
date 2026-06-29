"""Just-in-time context commands for verifier reporting."""

from __future__ import annotations


def context_commands(check_name: str, *, log_dir: str | None = None) -> tuple[str, str]:
    """Return just-in-time context commands for one failed check."""

    log_dir_arg = f" --log-dir {log_dir}" if log_dir else ""
    return (
        (
            "python -m agent_maintainer context"
            f"{log_dir_arg} failures --check {check_name} --limit 20"
        ),
        f"python -m agent_maintainer context{log_dir_arg} log {check_name} --tail 120",
    )
