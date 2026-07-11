"""Tests bounded context-pack ratchet behavior."""

from pathlib import Path

import pytest

from agent_maintainer.context.pack import ratchet as pack_ratchet


def test_bounded_pack_disables_live_ratchet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bounded caller does not activate repository-wide ratchet scans."""

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(pack_ratchet, "status_report", _forbidden_status)

    payload = pack_ratchet.ratchet_payload(
        baseline_path=baseline_path,
        base_ref="HEAD",
        target_limit=5,
        live_recompute=False,
    )

    assert payload["available"] is False
    assert "disabled" in str(payload["reason"])


def _forbidden_status(*args: object, **kwargs: object) -> object:
    """Fail when a bounded request reaches the live ratchet scan."""

    raise AssertionError("bounded context request reached live ratchet scan")
