"""Source-aware configuration diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigIssue:
    """One source-aware invalid configuration fact."""

    source: str
    key: str
    message: str

    def render(self) -> str:
        """Return a migration-quality one-line diagnostic."""

        return f"{self.source}: {self.key}: {self.message}"


class ConfigValidationError(TypeError):
    """Raised when any configuration source or merged policy is invalid."""

    def __init__(self, issues: tuple[ConfigIssue, ...]) -> None:
        self.issues = issues
        super().__init__("\n".join(issue.render() for issue in issues))
