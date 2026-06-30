"""Doctor checks for repository integration files."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.doctor.support import models as doctor_models

DoctorResult = doctor_models.DoctorResult
OK = doctor_models.OK
WARNING = doctor_models.WARNING
ERROR = doctor_models.ERROR

CLAUDE_HOOK_NAMES = ("post_tool_use.py", "stop.py", "subagent_stop.py")
CLAUDE_SETTINGS_MARKERS = (
    "agent_maintainer",
    "agent-maintainer hooks run",
    ".claude/hooks",
)
CANONICAL_COMMAND_EXPECTATIONS = (
    (".github/workflows/verify.yml", "python3 -m agent_maintainer verify"),
    (".pre-commit-config.yaml", "python3 -m agent_maintainer verify --profile precommit"),
    (".codex/hooks/post_edit_fast_gate.py", "agent_maintainer"),
    (".codex/hooks/stop_full_verify.py", "agent_maintainer"),
    (".claude/settings.json", ".claude/hooks"),
    (".claude/hooks/post_tool_use.py", "agent_maintainer"),
    (".claude/hooks/stop.py", "agent_maintainer"),
    (".claude/hooks/subagent_stop.py", "agent_maintainer"),
)


def check_pre_commit(repo_root: Path) -> DoctorResult:
    """Report whether the pre-commit config and hook are installed."""

    config_path = repo_root / ".pre-commit-config.yaml"
    hook_path = repo_root / ".git" / "hooks" / "pre-commit"
    if not config_path.exists():
        return DoctorResult(
            "pre-commit-hook",
            WARNING,
            ".pre-commit-config.yaml is absent.",
            state=doctor_models.NOT_APPLICABLE,
        )
    if not hook_path.exists():
        return DoctorResult(
            "pre-commit-hook",
            WARNING,
            "pre-commit hook is not installed.",
            state=doctor_models.MISSING,
            hint="Run python3 -m agent_maintainer install.",
        )
    return DoctorResult("pre-commit-hook", OK, ".git/hooks/pre-commit is installed.")


def check_codex_hooks(repo_root: Path) -> DoctorResult:
    """Report whether repo-local Codex hooks are configured."""

    config_path = repo_root / ".codex" / "config.toml"
    if not config_path.exists():
        return DoctorResult(
            "codex-hooks",
            WARNING,
            ".codex/config.toml is absent.",
            state=doctor_models.MISSING,
            hint="Run python3 -m agent_maintainer install.",
        )

    text = config_path.read_text(encoding="utf-8")
    if "hooks = true" not in text:
        return DoctorResult(
            "codex-hooks",
            WARNING,
            ".codex/config.toml does not enable hooks.",
            state=doctor_models.DISABLED,
            hint=("Set hooks = true if repo Codex hooks should enforce Agent Maintainer checks."),
        )
    return DoctorResult("codex-hooks", OK, ".codex/config.toml enables hooks.")


def check_claude_code_hooks(repo_root: Path) -> DoctorResult:
    """Report whether repo-local Claude Code hooks are configured."""

    settings_path = repo_root / ".claude" / "settings.json"
    hook_paths = tuple(
        repo_root / ".claude" / "hooks" / hook_name for hook_name in CLAUDE_HOOK_NAMES
    )

    if not settings_path.exists():
        return DoctorResult(
            "claude-code-hooks",
            WARNING,
            ".claude/settings.json is absent.",
            state=doctor_models.MISSING,
            hint="Run python3 -m agent_maintainer hooks install claude-code.",
        )
    missing = [path.relative_to(repo_root).as_posix() for path in hook_paths if not path.exists()]
    if missing:
        missing_files = ", ".join(missing)
        return DoctorResult(
            "claude-code-hooks",
            WARNING,
            f"Claude Code hook scripts missing: {missing_files}.",
            state=doctor_models.MISSING,
            hint="Run python3 -m agent_maintainer hooks install claude-code.",
        )

    text = settings_path.read_text(encoding="utf-8")
    if not any(marker in text for marker in CLAUDE_SETTINGS_MARKERS):
        return DoctorResult(
            "claude-code-hooks",
            WARNING,
            ".claude/settings.json does not reference Agent Maintainer hooks.",
            state=doctor_models.DISABLED,
            hint="Run python3 -m agent_maintainer hooks install claude-code.",
        )

    return DoctorResult(
        "claude-code-hooks",
        OK,
        ".claude/settings.json enables Agent Maintainer hooks.",
    )


def check_canonical_commands(repo_root: Path) -> DoctorResult:
    """Check that CI, pre-commit, and hooks use the module entrypoint."""

    missing = [
        path
        for path, _expected_text in CANONICAL_COMMAND_EXPECTATIONS
        if not (repo_root / path).exists()
    ]
    stale = [
        path
        for path, expected_text in CANONICAL_COMMAND_EXPECTATIONS
        if (repo_root / path).exists()
        and normalized_text(expected_text)
        not in normalized_text((repo_root / path).read_text(encoding="utf-8"))
    ]
    if stale:
        stale_paths = ", ".join(stale)
        return DoctorResult(
            "canonical-commands",
            ERROR,
            f"Stale command path in: {stale_paths}",
            state=doctor_models.UNSAFE_CONFIG,
            hint="Use python3 -m agent_maintainer in CI, pre-commit, and hooks.",
        )
    if missing:
        missing_paths = ", ".join(missing)
        return DoctorResult(
            "canonical-commands",
            WARNING,
            f"Missing command files: {missing_paths}",
            state=doctor_models.MISSING,
            hint=("Run python3 -m agent_maintainer install or add missing integration files."),
        )
    return DoctorResult(
        "canonical-commands",
        OK,
        "CI, pre-commit, and agent hooks use the module entrypoint.",
    )


def normalized_text(text: str) -> str:
    """Return text normalized for command substring checks."""

    return " ".join(text.split())
