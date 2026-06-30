"""Patch Mutmut config for advisory mutation sweep temp worktrees."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Final

from agent_maintainer.test_intel.mutation_sweep import MutationSweepCandidate

MUTMUT_SECTION: Final = "[tool.mutmut]"
MUTMUT_PATCH_KEYS: Final = (
    "only_mutate",
    "pytest_add_cli_args_test_selection",
)


def patch_mutmut_config(pyproject_path: Path, candidate: MutationSweepCandidate) -> None:
    """Patch Mutmut target config in a temporary pyproject file."""

    original_text = pyproject_path.read_text(encoding="utf-8")
    patched_text = replace_mutmut_targets(original_text, candidate)
    tomllib.loads(patched_text)
    pyproject_path.write_text(patched_text, encoding="utf-8")


def replace_mutmut_targets(text: str, candidate: MutationSweepCandidate) -> str:
    """Return pyproject text with Mutmut targets replaced."""

    lines = text.splitlines(keepends=True)
    section_start = mutmut_section_start(lines)
    section_end = next_section_start(lines, section_start + 1)
    section_lines = lines[section_start:section_end]
    patched_section = patch_mutmut_section(section_lines, candidate)
    return "".join([*lines[:section_start], *patched_section, *lines[section_end:]])


def mutmut_section_start(lines: list[str]) -> int:
    """Return the `[tool.mutmut]` section start index."""

    for index, line in enumerate(lines):
        if line.strip() == MUTMUT_SECTION:
            return index
    raise ValueError("pyproject.toml does not contain [tool.mutmut]")


def next_section_start(lines: list[str], start: int) -> int:
    """Return the next TOML section index."""

    for index, line in enumerate(lines[start:], start=start):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            return index
    return len(lines)


def patch_mutmut_section(
    section_lines: list[str],
    candidate: MutationSweepCandidate,
) -> list[str]:
    """Return a Mutmut section with advisory target replacements."""

    header = section_lines[:1]
    body = remove_toml_key_blocks(section_lines[1:], MUTMUT_PATCH_KEYS)
    replacement = [
        "\n",
        *format_toml_array("only_mutate", (candidate.path,)),
    ]
    if candidate.likely_tests:
        replacement.extend(
            format_toml_array(
                "pytest_add_cli_args_test_selection",
                candidate.likely_tests,
            ),
        )
    return [*header, *replacement, *trim_leading_blank_lines(body)]


def remove_toml_key_blocks(lines: list[str], keys: tuple[str, ...]) -> list[str]:
    """Remove TOML key blocks from a section body."""

    kept: list[str] = []
    skip_depth = 0
    for line in lines:
        if skip_depth > 0:
            skip_depth = max(0, skip_depth + bracket_depth(line))
            continue
        if toml_key_line(line, keys):
            skip_depth = max(bracket_depth(line), 0)
            continue
        kept.append(line)
    return kept


def toml_key_line(line: str, keys: tuple[str, ...]) -> bool:
    """Return whether line starts a TOML key assignment."""

    stripped = line.strip()
    return any(stripped.startswith(f"{key} =") for key in keys)


def bracket_depth(line: str) -> int:
    """Return simple bracket delta for TOML array skipping."""

    return line.count("[") - line.count("]")


def trim_leading_blank_lines(lines: list[str]) -> list[str]:
    """Return lines without leading blank lines."""

    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    return lines[index:]


def format_toml_array(key: str, values: tuple[str, ...]) -> list[str]:
    """Return TOML array assignment lines."""

    lines = [f"{key} = [\n"]
    lines.extend(f"  {json.dumps(value)},\n" for value in values)
    lines.append("]\n")
    return lines
