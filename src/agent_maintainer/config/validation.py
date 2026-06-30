"""Validation helpers for Agent Maintainer configuration tables."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from agent_maintainer.config import coercion, schema

DIAGNOSTICS_TABLE = "diagnostics"
TOOL_TABLE = "tool.agent_maintainer"
DIAGNOSTICS_PREFIX = f"{TOOL_TABLE}.{DIAGNOSTICS_TABLE}"


def known_top_level_keys() -> frozenset[str]:
    """Return supported keys under ``[tool.agent_maintainer]``."""

    return frozenset(field.name for field in fields(schema.MaintainerConfig)) | {
        DIAGNOSTICS_TABLE,
    }


def known_diagnostic_keys() -> frozenset[str]:
    """Return supported keys under ``[tool.agent_maintainer.diagnostics]``."""

    return frozenset(
        raw_name for raw_name, _field_name, _parser in coercion.DIAGNOSTIC_FIELD_PARSERS
    )


def unknown_keys(raw: dict[str, Any]) -> tuple[str, ...]:
    """Return unknown pyproject config key paths in deterministic order."""

    unknown = [f"{TOOL_TABLE}.{key}" for key in raw if key not in known_top_level_keys()]
    diagnostics = raw.get(DIAGNOSTICS_TABLE)
    if isinstance(diagnostics, dict):
        unknown.extend(
            f"{DIAGNOSTICS_PREFIX}.{key}"
            for key in diagnostics
            if key not in known_diagnostic_keys()
        )
    return tuple(sorted(unknown))
