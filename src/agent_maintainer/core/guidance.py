"""Generate agent-facing Agent Maintainer guidance from resolved config."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.core.config import MaintainerConfig, load_config
from agent_maintainer.ratchet.guidance import render_ratchet_guidance

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

    states = guidance_states(repo_root, config, output_path)
    for guidance_result in states:
        print(guidance_result.message)
    return 0 if all(result.status == CURRENT_STATUS for result in states) else 1


def guidance_states(
    repo_root: Path,
    config: MaintainerConfig,
    output_path: Path = DEFAULT_GUIDANCE_PATH,
) -> tuple[GuidanceState, ...]:
    """Return freshness states for every active guidance sidecar."""

    states = [guidance_state(repo_root, config, output_path)]
    if config.ratchet_enabled:
        ratchet_path = Path(config.ratchet_guidance_path)
        states.append(
            file_guidance_state(
                repo_root,
                ratchet_path,
                render_ratchet_guidance(config),
            ),
        )
    return tuple(states)


def guidance_state(
    repo_root: Path,
    config: MaintainerConfig,
    output_path: Path = DEFAULT_GUIDANCE_PATH,
) -> GuidanceState:
    """Return whether the generated guidance sidecar is current."""

    return file_guidance_state(repo_root, output_path, render_guidance(config))


def file_guidance_state(
    repo_root: Path,
    output_path: Path,
    expected: str,
) -> GuidanceState:
    """Return whether one generated guidance file is current."""

    path = repo_root / output_path
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
    if config.ratchet_enabled:
        ratchet_path = repo_root / config.ratchet_guidance_path
        ratchet_path.write_text(render_ratchet_guidance(config), encoding="utf-8")
    return path


def render_guidance(config: MaintainerConfig) -> str:
    """Render deterministic compact agent guidance from resolved config."""

    lines = [
        "# Generated Agent Maintainer Guidance",
        "",
        "Generated from `[tool.agent_maintainer]` by",
        "`python3 -m agent_maintainer guidance`. Do not edit by hand.",
        "Human reference: `docs/agent-maintainer-guidance.md`.",
        "Do not read it during normal coding unless changing guidance.",
        "",
        *ratchet_link_lines(config),
        "## Hard Rules",
        "",
        "- Keep commits small, tested, and aligned with configured boundaries.",
        "- Treat failing checks as design feedback before adding suppressions.",
        "- Update source, tests, docs, and config together when behavior changes.",
        "- Do not relax thresholds or architecture rules to make checks pass.",
        "",
        "## Context Hygiene",
        "",
        "- Check branch/worktree once at turn start and before staging.",
        "- Read long guidance files only when starting fresh, after compaction,",
        " or when guidance/config changed.",
        "- If already read in current unchanged context, use targeted `rg`",
        " for specific rules instead of re-reading whole guidance.",
        "- Prefer `rg --files` or `git ls-files` for file discovery.",
        "- Do not bulk-read generated/cache/binary paths:",
        "  `__pycache__`, `*.pyc`, `.venv`, `venv`, `.verify-logs`, `.coverage`,",
        "  `coverage.xml`, `htmlcov`, `mutants`, `build`, `dist`.",
        "- Use `AGENT_MAINTAINER_WRITE_BYTECODE=true` or",
        "  `AGENT_MAINTAINER_KEEP_MUTANTS=true` only when explicitly debugging",
        "  those artifacts.",
        "",
        "## Repo Contract",
        "",
        f"- Mode: `{config.mode}`",
        f"- Source roots: {format_inline_paths(config.source_roots)}",
        f"- Tests: {format_inline_paths(config.test_roots)}",
        f"- Architecture: `{config.architecture_tool}` with Tach domain contracts",
        "- If Tach policy changes, add or update an ADR under",
        "  `docs/architecture/decisions/`.",
        "",
        "## Blocking Limits",
        "",
        (
            "- Coverage floors: "
            f"total `{config.coverage_fail_under}%`, "
            f"changed `{config.diff_cover_fail_under}%`"
        ),
        (
            "- File length: "
            f"`{config.file_length_max_physical}` physical / "
            f"`{config.file_length_max_source}` source lines"
        ),
        (
            "- Change budget blocks: "
            f"`{config.change_block_lines}` lines or "
            f"`{config.change_block_files}` files"
        ),
        f"- New suppression budget: `{config.suppression_max_new}`",
        f"- Complexity: Ruff `{config.ruff_max_complexity}`, Xenon `{config.xenon_max_absolute}`",
        (
            "- Source-only changes without test-file changes: "
            f"{allowed_word(config.allow_source_without_test_change)}"
        ),
        "",
        *active_gate_lines(config),
        "",
        "## Failure Loop",
        "",
        "- Keep chat updates summary-first: completed check, actionable failure,",
        " or plan change.",
        "- Do not emit routine `still running` updates for expected long checks.",
        "- Use `apply_patch` for manual edits; avoid heredoc rewrite commands.",
        "- After a failed verifier or hook result, read the repair capsule or",
        " `.verify-logs/LAST_FAILURE.md` before changing code or config.",
        "- Prefer run-scoped `context --log-dir ...` commands for failures.",
        "- Expand only if needed:",
        " `python3 -m agent_maintainer context failures --limit 20`.",
        "- Fix the root cause; do not lower thresholds or add broad suppressions.",
        "",
        "## Required Commands",
        "",
        "- Prefer repo wrappers when present: `just verify-precommit`,",
        " `just verify`, `just verify-ci`, `just wait-github <run-id>`,",
        " `just wait-verifier <run-id>`.",
        "- Normal finish fallback: `just verify-precommit` only when trusted",
        " hooks are unavailable, bypassed, or failure reproduction is needed.",
        "- Trusted hooks already run `fast` after edits and `precommit`",
        " at stop; do not duplicate a same-state hook pass manually.",
        "- Larger/shared changes: after coherent final state, run one broad",
        " local profile, usually `full`.",
        "- Use `ci` locally instead of `full` when diff/base-ref,",
        " CI profile, or workflow behavior changed.",
        "- Run both `full` and `ci` only when verifier/profile/CI-diff",
        " behavior is under test.",
        "- Run `security` or `manual` when touching those gates, before release,",
        " or when explicitly requested.",
        "- For GitHub Actions or long verifier jobs, use",
        " `just wait-github <run-id>` or `just wait-verifier <run-id>`",
        " so tools own polling.",
        "- Run `just doctor` after setup, config, toolchain, hook,",
        " or initializer changes.",
        "",
        "## Escape Hatches",
        "",
        "- Prefer config or code fixes over one-off environment overrides.",
        "- Use cohesive change plans for intentional large diffs; include a reason",
        "  and verification plan.",
        "- If a check is wrong, make the smallest fix to the check, config, or docs.",
    ]
    lines.append("")
    return "\n".join(lines)


def active_gate_lines(config: MaintainerConfig) -> list[str]:
    """Return concise active gate guidance omitting disabled integrations."""

    gates = [
        *active_gate("pip-audit", config.enable_pip_audit),
        *active_gate("Mutmut", config.enable_mutmut),
        *active_gate("Semgrep", config.enable_semgrep),
        *active_gate("OSV Scanner", config.enable_osv_scanner),
        *active_gate("Trivy", config.enable_trivy),
        *active_gate("Python SBOM", config.enable_sbom),
        *active_gate("License checking", config.enable_license_check),
        *active_secret_scanning_gate(config),
        *active_boolean_gate("wemake-python-styleguide", config.enable_wemake),
        *active_boolean_gate("Interrogate", config.enable_interrogate),
        *active_gate("Markdown linting", config.enable_markdownlint),
        *active_gate("YAML linting", config.enable_yamllint),
        *active_gate("TOML formatting", config.enable_taplo),
        *active_gate(
            "Schema validation",
            config.enable_check_jsonschema,
        ),
    ]
    if not gates:
        return []
    return ["## Active Gates", "", *gates]


def active_gate(name: str, enabled: bool) -> list[str]:
    """Return one active gate line or no line when disabled."""

    if not enabled:
        return []
    return [f"- {name}"]


def active_boolean_gate(name: str, enabled: bool) -> list[str]:
    """Return one active boolean gate line."""

    return [f"- {name}"] if enabled else []


def active_secret_scanning_gate(config: MaintainerConfig) -> list[str]:
    """Return active secret-scanning gate summary."""

    if not config.enable_secret_scanning:
        return []
    return [f"- Secret scanning: {config.secret_scanner}"]


def ratchet_link_lines(config: MaintainerConfig) -> list[str]:
    """Return main-guidance ratchet link lines when active."""

    if not config.ratchet_enabled:
        return []
    return [
        "## Ratchet Guidance",
        "",
        f"- Read `{config.ratchet_guidance_path}` for legacy ratchet repair guidance.",
        "",
    ]


def format_inline_paths(paths: tuple[str, ...]) -> str:
    """Format configured paths as Markdown inline code."""

    if not paths:
        return "`<none>`"
    return ", ".join(f"`{path}`" for path in paths)


def allowed_word(enabled: bool) -> str:
    """Return a compact allowed/blocked token."""

    return "`allowed`" if enabled else "`blocked`"


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
