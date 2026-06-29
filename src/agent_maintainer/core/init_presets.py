"""Starter configuration presets for repository onboarding."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_PRESET = "existing-app"
SMALL_LIBRARY_PRESET = "small-library"
EXISTING_APP_PRESET = "existing-app"
AI_AGENT_HEAVY_PRESET = "ai-agent-heavy"
LEGACY_RATCHET_PRESET = "legacy-ratchet"
STRICT_NEW_REPO_PRESET = "strict-new-repo"

PRESETS = (
    SMALL_LIBRARY_PRESET,
    EXISTING_APP_PRESET,
    AI_AGENT_HEAVY_PRESET,
    LEGACY_RATCHET_PRESET,
    STRICT_NEW_REPO_PRESET,
)


@dataclass(frozen=True)
class PresetNumbers:
    """Named numeric policy values used by onboarding presets."""

    coverage_existing: int = 80
    coverage_legacy: int = 70
    coverage_strict: int = 90
    diff_legacy: int = 80
    file_physical_default: int = 600
    file_physical_legacy: int = 800
    file_physical_strict: int = 500
    file_source_default: int = 450
    file_source_legacy: int = 600
    file_source_strict: int = 375
    warn_lines_default: int = 300
    warn_lines_legacy: int = 500
    warn_lines_strict: int = 200
    warn_lines_strict_new: int = 150
    block_lines_default: int = 800
    block_lines_legacy: int = 1_200
    block_lines_strict: int = 600
    block_lines_strict_new: int = 500
    warn_files_default: int = 8
    warn_files_legacy: int = 12
    warn_files_strict: int = 6
    warn_files_strict_new: int = 5
    block_files_default: int = 20
    block_files_legacy: int = 30
    block_files_strict: int = 12
    block_files_strict_new: int = 10
    suppression_default: int = 3
    suppression_legacy: int = 5
    suppression_strict: int = 1
    suppression_zero: int = 0
    complexity_default: int = 10
    complexity_strict: int = 8


@dataclass(frozen=True)
class PresetPolicy:
    """Starter config values for one onboarding preset."""

    mode: str = "custom"
    coverage_fail_under: int = PresetNumbers.coverage_existing
    diff_cover_fail_under: int = PresetNumbers.coverage_strict
    file_length_max_physical: int = PresetNumbers.file_physical_default
    file_length_max_source: int = PresetNumbers.file_source_default
    change_warn_lines: int = PresetNumbers.warn_lines_default
    change_block_lines: int = PresetNumbers.block_lines_default
    change_warn_files: int = PresetNumbers.warn_files_default
    change_block_files: int = PresetNumbers.block_files_default
    source_without_test_profiles: tuple[str, ...] = ()
    suppression_max_new: int = PresetNumbers.suppression_default
    ruff_max_complexity: int = PresetNumbers.complexity_default
    pyright_type_checking_mode: str = "standard"
    ratchet_enabled: bool = False
    file_length_baseline: str | None = None
    enable_wemake: bool = False


NUMBERS = PresetNumbers()
SOURCE_WITHOUT_TEST_PROFILES = ("precommit", "full", "ci")
LEGACY_FILE_LENGTH_BASELINE = ".agent-maintainer/file-length-baseline.json"

POLICIES = (
    (EXISTING_APP_PRESET, PresetPolicy()),
    (
        SMALL_LIBRARY_PRESET,
        PresetPolicy(
            coverage_fail_under=NUMBERS.coverage_strict,
            file_length_max_physical=NUMBERS.file_physical_strict,
            file_length_max_source=NUMBERS.file_source_strict,
            change_warn_lines=NUMBERS.warn_lines_strict,
            change_block_lines=NUMBERS.block_lines_strict,
            change_warn_files=NUMBERS.warn_files_strict,
            change_block_files=NUMBERS.block_files_strict,
            suppression_max_new=NUMBERS.suppression_strict,
            ruff_max_complexity=NUMBERS.complexity_strict,
        ),
    ),
    (
        AI_AGENT_HEAVY_PRESET,
        PresetPolicy(
            mode="fresh-strict",
            coverage_fail_under=NUMBERS.coverage_strict,
            file_length_max_physical=NUMBERS.file_physical_strict,
            file_length_max_source=NUMBERS.file_source_strict,
            change_warn_lines=NUMBERS.warn_lines_strict,
            change_block_lines=NUMBERS.block_lines_strict,
            change_warn_files=NUMBERS.warn_files_strict,
            change_block_files=NUMBERS.block_files_strict,
            source_without_test_profiles=SOURCE_WITHOUT_TEST_PROFILES,
            suppression_max_new=NUMBERS.suppression_strict,
            ruff_max_complexity=NUMBERS.complexity_strict,
        ),
    ),
    (
        LEGACY_RATCHET_PRESET,
        PresetPolicy(
            mode="legacy-ratchet",
            coverage_fail_under=NUMBERS.coverage_legacy,
            diff_cover_fail_under=NUMBERS.diff_legacy,
            file_length_max_physical=NUMBERS.file_physical_legacy,
            file_length_max_source=NUMBERS.file_source_legacy,
            change_warn_lines=NUMBERS.warn_lines_legacy,
            change_block_lines=NUMBERS.block_lines_legacy,
            change_warn_files=NUMBERS.warn_files_legacy,
            change_block_files=NUMBERS.block_files_legacy,
            suppression_max_new=NUMBERS.suppression_legacy,
            ratchet_enabled=True,
            file_length_baseline=LEGACY_FILE_LENGTH_BASELINE,
        ),
    ),
    (
        STRICT_NEW_REPO_PRESET,
        PresetPolicy(
            mode="fresh-strict",
            coverage_fail_under=NUMBERS.coverage_strict,
            file_length_max_physical=NUMBERS.file_physical_strict,
            file_length_max_source=NUMBERS.file_source_strict,
            change_warn_lines=NUMBERS.warn_lines_strict_new,
            change_block_lines=NUMBERS.block_lines_strict_new,
            change_warn_files=NUMBERS.warn_files_strict_new,
            change_block_files=NUMBERS.block_files_strict_new,
            source_without_test_profiles=SOURCE_WITHOUT_TEST_PROFILES,
            suppression_max_new=NUMBERS.suppression_zero,
            ruff_max_complexity=NUMBERS.complexity_strict,
            pyright_type_checking_mode="strict",
            enable_wemake=True,
        ),
    ),
)


def apply_preset(template: str, preset: str) -> str:
    """Return starter pyproject text tuned for an onboarding preset."""

    policy = policy_for(preset)
    text = template.replace(
        "# Starter Agent Maintainer config for package-first adoption.",
        (
            "# Starter Agent Maintainer config for package-first adoption.\n"
            f"# Onboarding preset: {preset}."
        ),
        1,
    )
    replacements = (
        ("mode", quoted(policy.mode)),
        ("coverage_fail_under", str(policy.coverage_fail_under)),
        ("diff_cover_fail_under", str(policy.diff_cover_fail_under)),
        ("file_length_max_physical", str(policy.file_length_max_physical)),
        ("file_length_max_source", str(policy.file_length_max_source)),
        ("change_warn_lines", str(policy.change_warn_lines)),
        ("change_block_lines", str(policy.change_block_lines)),
        ("change_warn_files", str(policy.change_warn_files)),
        ("change_block_files", str(policy.change_block_files)),
        (
            "source_without_test_change_error_profiles",
            list_literal(policy.source_without_test_profiles),
        ),
        ("suppression_max_new", str(policy.suppression_max_new)),
        ("ruff_max_complexity", str(policy.ruff_max_complexity)),
        ("pyright_type_checking_mode", quoted(policy.pyright_type_checking_mode)),
        ("ratchet_enabled", bool_literal(policy.ratchet_enabled)),
        ("enable_wemake", bool_literal(policy.enable_wemake)),
    )
    for key, value in replacements:
        text = replace_assignment(text, key, value)
    if policy.file_length_baseline is not None:
        text = insert_after_assignment(
            text,
            "file_length_max_source",
            f'file_length_baseline = "{policy.file_length_baseline}"',
        )
    return text


def policy_for(preset: str) -> PresetPolicy:
    """Return policy for preset name."""

    for name, policy in POLICIES:
        if name == preset:
            return policy
    raise ValueError(f"unknown onboarding preset: {preset}")


def replace_assignment(text: str, key: str, value: str) -> str:
    """Replace one top-level TOML assignment in template text."""

    lines = text.splitlines()
    prefix = f"{key} = "
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{key} = {value}"
            return join_lines(lines)
    raise ValueError(f"starter config key not found: {key}")


def insert_after_assignment(text: str, key: str, line_to_insert: str) -> str:
    """Insert a line after a top-level TOML assignment."""

    lines = text.splitlines()
    if line_to_insert in lines:
        return text
    prefix = f"{key} = "
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines.insert(index + 1, line_to_insert)
            return join_lines(lines)
    raise ValueError(f"starter config key not found: {key}")


def quoted(value: str) -> str:
    """Return TOML string literal for a simple value."""

    return f'"{value}"'


def bool_literal(value: bool) -> str:
    """Return TOML boolean literal."""

    return "true" if value else "false"


def list_literal(values: tuple[str, ...]) -> str:
    """Return compact TOML list literal for string values."""

    if not values:
        return "[]"
    joined = ", ".join(quoted(value) for value in values)
    return f"[{joined}]"


def join_lines(lines: list[str]) -> str:
    """Return newline-terminated text from lines."""

    return "\n".join((*lines, ""))
