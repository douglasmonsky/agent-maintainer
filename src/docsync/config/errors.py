"""DocSync configuration and filesystem policy errors."""

from __future__ import annotations


class PathBoundaryError(ValueError):
    """Raised when a DocSync path crosses its approved repository boundary."""


class ConfigError(ValueError):
    """Raised when DocSync configuration cannot be loaded."""
