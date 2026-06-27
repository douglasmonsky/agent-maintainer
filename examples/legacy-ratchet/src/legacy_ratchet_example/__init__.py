"""Tiny package used by the legacy-ratchet Agent Maintainer example."""


def normalize_label(value: str) -> str:
    """Normalize user-visible labels in a conservative legacy-friendly way."""
    return " ".join(value.strip().split())
