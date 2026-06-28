"""Generate agent-facing Agent Maintainer guidance from resolved config."""

from __future__ import annotations

import argparse
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.core.config import MaintainerConfig, load_config

DEFAULT_GUIDANCE_PATH = Path("AGENTS.agent-maintainer.md")
CURRENT_STATUS = "current"
MISSING_STATUS = "missing"
STALE_STATUS = "stale"


@dataclass(frozen=True)
class GuidanceState:
    """Freshness state for generated maintainer guidance."""

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


def check_guidance(repo_root: Path, config: MaintainerConfig, output_path: Path) -> int:
    """Report whether generated guidance matches current config."""

    state = guidance_state(repo_root, config, output_path)
    print(state.message)
    return 0 if state.status == CURRENT_STATUS else 1


def guidance_state(
    repo_root: Path,
    config: MaintainerConfig,
    output_path: Path = DEFAULT_GUIDANCE_PATH,
) -> GuidanceState:
    """Return whether the generated guidance sidecar is current."""

    path = repo_root / output_path
    expected = render_guidance(config)
    if not path.exists():
        return GuidanceState(
            MISSING_STATUS,
            output_path,
            f"{output_path.as_posix()} is missing; run python3 -m agent_maintainer guidance.",
        )
    if path.read_text(encoding="utf-8") != expected:
        return GuidanceState(
            STALE_STATUS,
            output_path,
            f"{output_path.as_posix()} is stale; run python3 -m agent_maintainer guidance.",
        )
    return GuidanceState(CURRENT_STATUS, output_path, f"{output_path.as_posix()} is current.")


def write_guidance(
    repo_root: Path,
    config: MaintainerConfig,
    output_path: Path = DEFAULT_GUIDANCE_PATH,
) -> Path:
    """Write generated maintainer guidance and return the written path."""

    path = repo_root / output_path
    path.write_text(render_guidance(config), encoding="utf-8")
    return path


def render_guidance(config: MaintainerConfig) -> str:
    """Render deterministic agent guidance for a resolved config."""

    tests_required = str(config.require_tests).lower()
    lines = [
        "# Generated Agent Maintainer Guidance",
        "",
        "This file is generated from `[tool.agent_maintainer]` by",
        "`python3 -m agent_maintainer guidance`. Do not edit it by hand; update",
        "configuration first, then regenerate it.",
        "",
        "## Operating Intent",
        "",
        "- Prefer small, coherent commits that keep maintenance feedback easy to review.",
        "- Keep source, tests, documentation, and configuration moving together.",
        "- Treat failing checks as design feedback before reaching for suppressions.",
        "- Preserve the configured architecture boundaries instead of adding imports around them.",
        "- Add or update tests for behavior changes unless tests are explicitly disabled.",
        "",
        "## File Inspection Safety",
        "",
        "- Prefer `rg --files` or `git ls-files` when enumerating files to inspect.",
        "- Restrict bulk reads to relevant text/source globs instead of every file under a tree.",
        "- Do not read generated or binary artifacts unless the task explicitly targets them:",
        "  `__pycache__`, `*.pyc`, `.venv`, `venv`, `.verify-logs`, `.coverage`,",
        "  `coverage.xml`, `htmlcov`, `mutants`, `build`, and `dist`.",
        "- Agent Maintainer and hook subprocesses set `PYTHONDONTWRITEBYTECODE=1` by",
        "  default. Set `AGENT_MAINTAINER_WRITE_BYTECODE=true` only when explicitly",
        "  debugging bytecode-cache behavior.",
        "- Manual Mutmut runs remove `mutants` after success. Set",
        "  `AGENT_MAINTAINER_KEEP_MUTANTS=true` only when explicitly debugging",
        "  mutation artifacts.",
        "- When a broad command is unavoidable, exclude generated, binary, cache, and",
        "  virtualenv paths before printing file contents.",
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
        "## Architecture Policy Changes",
        "",
        "- `tach.toml`, `tach.domain.toml`, and architecture boundary",
        " configuration are policy files.",
        "- If a policy file changes, add or update a decision note under",
        " `docs/architecture/decisions/`.",
        "- The note must explain why the policy change is intentional and why",
        " it is not architecture drift.",
        "- Prefer refactoring code to preserve an existing boundary before",
        " changing the boundary.",
        "",
        "## Verification Flow",
        "",
        "- Trusted agent hooks normally run fast checks after edits and the precommit profile",
        "  before completion.",
        "- Run the precommit profile manually when hooks are unavailable, after bypassing hooks,",
        "  or when reproducing a hook failure:",
        "  `python3 -m agent_maintainer verify --profile precommit`.",
        "- Run the full profile before merging larger changes or changing shared verifier logic:",
        "  `python3 -m agent_maintainer verify --profile full`.",
        "- After changing `[tool.agent_maintainer]`, run",
        "  `python3 -m agent_maintainer guidance` and `python3 -m agent_maintainer doctor`.",
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
        (
            "- Folder Python-file warning/block thresholds: "
            f"`{config.folder_file_warn}` / `{config.folder_file_block}` "
            "(block active in fresh-strict)"
        ),
        (
            "- Structure hint patterns are advisory refactor prompts; split by "
            "responsibility when a folder no longer has one clear boundary."
        ),
        "",
        "## Optional Gates",
        "",
        f"- pip-audit: {enabled_with_args(config.enable_pip_audit, config.pip_audit_args)}",
        f"- Mutmut: {enabled_with_args(config.enable_mutmut, config.mutmut_args)}",
        f"- Semgrep: {enabled_with_args(config.enable_semgrep, config.semgrep_args)}",
        f"- OSV Scanner: {enabled_with_args(config.enable_osv_scanner, config.osv_scanner_args)}",
        f"- Trivy: {enabled_with_args(config.enable_trivy, config.trivy_args)}",
        f"- Python SBOM: {enabled_with_args(config.enable_sbom, config.sbom_args)}",
        (
            "- License checking: "
            f"{enabled_with_args(config.enable_license_check, config.license_check_args)}"
        ),
        f"- Secret scanning: {secret_scanning_summary(config)}",
        f"- wemake-python-styleguide: {enabled_word(config.enable_wemake)}",
        f"- Interrogate: {enabled_word(config.enable_interrogate)}",
        (
            "- Markdown linting: "
            f"{enabled_with_args(config.enable_markdownlint, config.markdownlint_paths)}"
        ),
        f"- YAML linting: {enabled_with_args(config.enable_yamllint, config.yamllint_paths)}",
        f"- TOML formatting: {enabled_with_args(config.enable_taplo, config.taplo_paths)}",
        (
            "- Schema validation: "
            f"{enabled_with_args(config.enable_check_jsonschema, config.check_jsonschema_args)}"
        ),
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
        "- If a check is wrong, make the smallest correction to the check, config, or docs.",
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


def secret_scanning_summary(config: MaintainerConfig) -> str:
    """Return enabled secret scanner backend and profile summary."""
    if not config.enable_secret_scanning:
        return "`disabled`"
    profiles = ", ".join(config.secret_scan_profiles) or "none"
    history_profiles = ", ".join(config.secret_scan_history_profiles) or "none"
    return (
        f"enabled with `{config.secret_scanner}` "
        f"(profiles: {profiles}; history: {history_profiles})"
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
