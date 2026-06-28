"""Tests deterministic context sanitization."""

from __future__ import annotations

from agent_maintainer.context.sanitize import sanitize_text


def test_sanitize_text_redacts_common_secret_shapes() -> None:
    """Sanitization removes common tokens without external dependencies."""

    raw_text = "\n".join(
        (
            "Authorization: Bearer abc123",
            "API_TOKEN=secret-value",
            "password=not-uppercase-is-left-alone",
            "openai_key=sk-proj-abcdefghijklmnopqrstuvwxyz",
            "-----BEGIN PRIVATE KEY-----",
            "abc123",
            "-----END PRIVATE KEY-----",
        )
    )

    sanitized = sanitize_text(raw_text)

    assert "Authorization: [REDACTED]" in sanitized
    assert "API_TOKEN=[REDACTED]" in sanitized
    assert "[REDACTED API KEY]" in sanitized
    assert "[REDACTED PRIVATE KEY]" in sanitized
    assert "abc123" not in sanitized
