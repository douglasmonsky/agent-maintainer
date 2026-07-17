"""Coercion tests for provider-neutral and ecosystem extension tables."""

from __future__ import annotations

import pytest

from agent_maintainer.config import coercion


def test_file_baseline_path_is_coerced() -> None:
    """The provider-neutral baseline path keeps its public configuration value."""

    updates = coercion.coerce_file_baselines(
        {"baseline": ".agent-maintainer/file-baselines.json"},
    )

    assert updates["file_baselines_baseline"] == ".agent-maintainer/file-baselines.json"


def test_file_baseline_path_error_keeps_public_field_name() -> None:
    """Invalid baseline paths identify the nested public field."""

    with pytest.raises(
        TypeError,
        match=r"^file_baselines\.baseline must be a non-empty string$",
    ):
        coercion.coerce_file_baselines({"baseline": object()})


def test_coerce_updates_forwards_source_to_java(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The aggregate coercion boundary preserves Java diagnostic provenance."""

    observed: list[str] = []
    sentinel = object()

    def fake_java(
        raw_value: object,
        *,
        source: str = coercion.DEFAULT_CONFIG_SOURCE,
    ) -> object:
        del raw_value
        observed.append(source)
        return sentinel

    monkeypatch.setattr(coercion, "coerce_java", fake_java)

    updates = coercion.coerce_updates({"java": {}}, source="settings.toml")

    assert updates["java"] is sentinel
    assert observed == ["settings.toml"]
