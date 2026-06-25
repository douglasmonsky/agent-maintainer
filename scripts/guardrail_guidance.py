"""Generate agent-facing guidance from resolved guardrail configuration."""

from __future__ import annotations

import argparse
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

from scripts.guardrail_config import GuardrailConfig, load_config

DEFAULT_GUIDANCE_PATH = Path("AGENTS.guardrails.md")
CURRENT_STATUS = "current"
MISSING_STATUS = "missing"
STALE_STATUS = "stale"


@dataclass(frozen=True)
class GuidanceState:
    """Freshness state for generated guardrail guidance."""

    status: str
    path: Path
    message: str


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse generated guidance command options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit nonzero when the generated guidance sidecar is missing or stale.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_GUIDANCE_PATH),
        help="Generated guidance path relative to the repository root.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Write or check generated agent guidance."""

    args = parse_args(argv)
    repo_root = Path.cwd()
    output_path = Path(args.output)
    config = load_config()
    if args.check:
        return check_guidance(repo_root, config, output_path)
    write_guidance(repo_root, config, output_path)
    print(f"Wrote {output_path.as_posix()}.")
    return 0


def check_guidance(repo_root: Path, config: GuardrailConfig, output_path: Path) -> int:
    """Report whether generated guidance matches current config."""

    state = guidance_state(repo_root, config, output_path)
    print(state.message)
    return 0 if state.status == CURRENT_STATUS else 1


def guidance_state(
    repo_root: Path,
    config: GuardrailConfig,
    output_path: Path = DEFAULT_GUIDANCE_PATH,
) -> GuidanceState:
    """Return whether the generated guidance sidecar is current."""

    path = repo_root / output_path
    expected = render_guidance(config)
    if not path.exists():
        return GuidanceState(
            MISSING_STATUS,
            output_path,
            f"{output_path.as_posix()} is missing; run python3 -m scripts.guardrail guidance.",
        )
    if path.read_text(encoding="utf-8") != expected:
        return GuidanceState(
            STALE_STATUS,
            output_path,
            f"{output_path.as_posix()} is stale; run python3 -m scripts.guardrail guidance.",
        )
    return GuidanceState(CURRENT_STATUS, output_path, f"{output_path.as_posix()} is current.")


def write_guidance(
    repo_root: Path,
    config: GuardrailConfig,
    output_path: Path = DEFAULT_GUIDANCE_PATH,
) -> Path:
    """Write generated guardrail guidance and return the written path."""

    path = repo_root / output_path
    path.write_text(render_guidance(config), encoding="utf-8")
    return path


def render_guidance(config: GuardrailConfig) -> str:
    """Render deterministic agent guidance for a resolved config."""

    tests_required = str(config.require_tests).lower()
    lines = [
        "# Generated Guardrail Guidance",
        "",
        "This file is generated from `[tool.ai_guardrails]` by",
        "`python3 -m scripts.guardrail guidance`. Do not edit it by hand; update",
        "configuration first, then regenerate it.",
        "",
        "## Operating Intent",
        "",
        "- Prefer small, coherent commits that keep guardrail feedback easy to review.",
        "- Keep source, tests, documentation, and configuration moving together.",
        "- Treat failing checks as design feedback before reaching for suppressions.",
        "- Preserve the configured architecture boundaries instead of adding imports around them.",
        "- Add or update tests for behavior changes unless tests are explicitly disabled.",
        "",
        "## Active Configuration",
        "",
        f"- Mode: `{config.mode}`",
        f"- Source roots: {format_inline_paths(config.source_roots)}",
        f"- Test roots: {format_inline_paths(config.test_roots)}",
        f"- Package paths: {format_inline_paths(config.package_paths)}",
        f"- Coverage source: {format_inline_paths(config.coverage_source)}",
        f"- Architecture backend: `{config.architecture_tool}`",
        f"- Tests required: `{tests_required}`",
        (
            "- Diagnostic artifacts: "
            f"{enabled_word(config.diagnostic_artifacts_enabled)} at "
            f"`{config.diagnostic_artifacts_dir}`"
        ),
        (
            "- Source-without-test-change errors in profiles: "
            f"{format_inline_paths(config.source_without_test_change_error_profiles)}"
        ),
        (
            "- Source-only changes without test-file changes: "
            f"{allowed_word(config.allow_source_without_test_change)}"
        ),
        "",
        "## Verification Flow",
        "",
        "- Trusted Codex hooks normally run fast checks after edits and the precommit profile",
        "  before completion.",
        "- Run the precommit profile manually when hooks are unavailable, after bypassing hooks,",
        "  or when reproducing a hook failure:",
        "  `python3 -m scripts.guardrail verify --profile precommit`.",
        "- Run the full profile before merging larger changes or changing shared guardrail logic:",
        "  `python3 -m scripts.guardrail verify --profile full`.",
        "- After changing `[tool.ai_guardrails]`, run",
        "  `python3 -m scripts.guardrail guidance` and `python3 -m scripts.guardrail doctor`.",
        "",
        "## Thresholds To Preserve",
        "",
        f"- Total coverage floor: `{config.coverage_fail_under}%`",
        f"- Changed-code coverage floor: `{config.diff_cover_fail_under}%`",
        (
            "- File length limits: "
            f"`{config.file_length_max_physical}` physical lines, "
            f"`{config.file_length_max_source}` source lines"
        ),
        f"- File length baseline: {disabled_or_path(config.file_length_baseline)}",
        (
            "- Change budget warnings: "
            f"`{config.change_warn_lines}` lines or `{config.change_warn_files}` files"
        ),
        (
            "- Change budget blocks: "
            f"`{config.change_block_lines}` lines or `{config.change_block_files}` files"
        ),
        f"- New suppression budget: `{config.suppression_max_new}`",
        f"- Ruff McCabe complexity: `{config.ruff_max_complexity}`",
        (
            "- Xenon complexity: "
            f"absolute `{config.xenon_max_absolute}`, modules `{config.xenon_max_modules}`, "
            f"average `{config.xenon_max_average}`"
        ),
        f"- Pyright mode: `{config.pyright_type_checking_mode}`",
        f"- Interrogate floor: `{config.interrogate_fail_under}%`",
        "",
        "## Optional Gates",
        "",
        f"- pip-audit: {enabled_with_args(config.enable_pip_audit, config.pip_audit_args)}",
        f"- wemake-python-styleguide: {enabled_word(config.enable_wemake)}",
        f"- Interrogate: {enabled_word(config.enable_interrogate)}",
        "",
        "## Escape Hatches",
        "",
        "- Prefer config changes over one-off command drift when repository layout changes.",
        "- Keep temporary CLI or environment overrides out of committed config "
        "unless they are policy.",
        "- Use `require_tests = false` only for repositories that intentionally have no tests.",
        (
            "- Use `allow_source_without_test_change = true` only when existing "
            "tests already cover the change."
        ),
        "- If a guardrail is wrong, make the smallest correction to the check, config, or docs.",
    ]
    lines.append("")
    return "\n".join(lines)


def format_inline_paths(paths: tuple[str, ...]) -> str:
    """Format configured paths as Markdown inline code."""

    if not paths:
        return "`<none>`"
    return ", ".join(f"`{path}`" for path in paths)


def enabled_word(enabled: bool) -> str:
    """Return a compact enabled/disabled token."""

    return "`enabled`" if enabled else "`disabled`"


def disabled_or_path(value: str) -> str:
    """Return a compact disabled token or inline path."""

    return f"`{value}`" if value else "`disabled`"


def allowed_word(enabled: bool) -> str:
    """Return a compact allowed/blocked token."""

    return "`allowed`" if enabled else "`blocked`"


def enabled_with_args(enabled: bool, args: tuple[str, ...]) -> str:
    """Return enabled state plus command arguments when present."""

    if not enabled:
        return "`disabled`"
    if not args:
        return "`enabled` with no pinned input"
    return f"enabled with `{shlex.join(args)}`"


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
