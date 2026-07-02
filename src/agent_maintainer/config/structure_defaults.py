"""Default structure-cohesion path and hint settings."""

from __future__ import annotations

DEFAULT_STRUCTURE_IGNORE_PATHS = (
    "tests/**",
    "migrations/**",
    "generated/**",
    ".venv/**",
    "venv/**",
    "**/__pycache__/**",
)

DEFAULT_STRUCTURE_HINT_PATTERNS = (
    r"^maintainer_",
    r"^check_",
    r"^user_",
    r"^course_",
    r"_model$",
    r"_service$",
    r"_repository$",
    r"_client$",
    r"_adapter$",
    r"_parser$",
    r"_loader$",
    r"_schema$",
    r"_executor$",
    r"_reporting$",
    r"^(cli|args|config|models|checks|doctor|executor|reporting)$",
)
