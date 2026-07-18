"""Canonical generated contract baseline tests."""

import json
import stat
from dataclasses import replace
from pathlib import Path

import pytest

from agent_maintainer.contracts import baseline_write
from agent_maintainer.contracts.baseline import (
    canonical_json,
    fingerprint,
    load_baseline,
    parse_baseline,
    render_baseline,
    write_baseline_atomic,
)
from agent_maintainer.contracts.models import BaselineError, ContractBaseline, Descriptor

BASELINE_MODE = 0o600


def test_canonical_json_is_compact_and_key_sorted() -> None:
    """Semantic helpers receive one compact deterministic JSON encoding."""
    assert canonical_json({"z": 1, "a": [2]}) == '{"a":[2],"z":1}'


def _descriptor(contract_id: str = "docsync-api") -> Descriptor:
    return Descriptor(
        contract_id=contract_id,
        kind="python-api",
        owner="docsync.api",
        stability="beta",
        revision=1,
        sources=("src/docsync/api.py",),
        body={"exports": [{"name": "check_repo", "kind": "function"}]},
        fingerprint="",
    )


def _baseline() -> ContractBaseline:
    descriptor = _descriptor()
    semantic = {
        "body": descriptor.body,
        "contract_id": descriptor.contract_id,
        "kind": descriptor.kind,
        "owner": descriptor.owner,
        "revision": descriptor.revision,
        "sources": list(descriptor.sources),
        "stability": descriptor.stability,
    }
    descriptor = replace(descriptor, fingerprint=fingerprint(semantic))
    return ContractBaseline(package_version="0.1.0b10", descriptors=(descriptor,))


def _refingerprint(payload: dict[str, object]) -> None:
    payload.pop("document_fingerprint", None)
    payload["document_fingerprint"] = fingerprint(payload)


def test_render_baseline_is_byte_stable_and_round_trips() -> None:
    """Identical semantic evidence produces identical canonical JSON."""
    first = render_baseline(_baseline())
    second = render_baseline(_baseline())

    assert first == second
    assert first.endswith("\n")
    assert "created_at" not in first
    assert parse_baseline(first, source="baseline.json").descriptors == _baseline().descriptors


def test_tampered_descriptor_fingerprint_fails_closed() -> None:
    """Descriptor bodies cannot be changed without invalidating evidence."""
    payload = json.loads(render_baseline(_baseline()))
    payload["descriptors"][0]["fingerprint"] = "sha256:" + "0" * 64
    _refingerprint(payload)

    with pytest.raises(BaselineError, match="descriptor fingerprint"):
        parse_baseline(json.dumps(payload), source="baseline.json")


@pytest.mark.parametrize(
    ("key", "value", "message"),
    (
        ("schema_version", 2, "schema_version"),
        ("generator", "other-tool", "generator"),
    ),
)
def test_baseline_rejects_unsupported_document_identity(
    key: str,
    value: object,
    message: str,
) -> None:
    """Generated evidence has one supported schema and generator identity."""
    payload = json.loads(render_baseline(_baseline()))
    payload[key] = value
    _refingerprint(payload)

    with pytest.raises(BaselineError, match=message):
        parse_baseline(json.dumps(payload), source="baseline.json")


def test_baseline_rejects_duplicate_contracts() -> None:
    """A contract identity appears exactly once in generated evidence."""
    payload = json.loads(render_baseline(_baseline()))
    payload["descriptors"].append(payload["descriptors"][0])
    _refingerprint(payload)

    with pytest.raises(BaselineError, match="duplicate baseline contract"):
        parse_baseline(json.dumps(payload), source="baseline.json")


def test_baseline_rejects_noncanonical_source_paths() -> None:
    """Descriptor evidence cannot name absolute or escaping source paths."""
    payload = json.loads(render_baseline(_baseline()))
    descriptor = payload["descriptors"][0]
    descriptor["sources"] = ["../api.py"]
    semantic = dict(descriptor)
    semantic.pop("fingerprint")
    descriptor["fingerprint"] = fingerprint(semantic)
    _refingerprint(payload)

    with pytest.raises(BaselineError, match="unsafe or ambiguous"):
        parse_baseline(json.dumps(payload), source="baseline.json")


@pytest.mark.parametrize("sources", (["z.py", "a.py"], ["a.py", "a.py"]))
def test_baseline_requires_sorted_unique_sources(sources: list[str]) -> None:
    """Descriptor source evidence has one canonical order without aliases."""
    payload = json.loads(render_baseline(_baseline()))
    descriptor = payload["descriptors"][0]
    descriptor["sources"] = sources
    semantic = dict(descriptor)
    semantic.pop("fingerprint")
    descriptor["fingerprint"] = fingerprint(semantic)
    _refingerprint(payload)

    with pytest.raises(BaselineError, match="sources must be sorted and unique"):
        parse_baseline(json.dumps(payload), source="baseline.json")


def test_atomic_write_replaces_exact_baseline(tmp_path: Path) -> None:
    """Baseline writing creates the configured file and preserves canonical bytes."""
    relative = Path(".agent-maintainer/contracts-baseline.json")

    write_baseline_atomic(tmp_path, relative, _baseline())

    assert (tmp_path / relative).read_text(encoding="utf-8") == render_baseline(_baseline())
    assert load_baseline(tmp_path, relative) == parse_baseline(
        render_baseline(_baseline()),
        source=relative.as_posix(),
    )
    assert stat.S_IMODE((tmp_path / relative).stat().st_mode) == BASELINE_MODE


def test_baseline_symlink_is_rejected(tmp_path: Path) -> None:
    """A baseline destination cannot replace or follow a symlink."""
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    directory = tmp_path / ".agent-maintainer"
    directory.mkdir()
    link = directory / "contracts-baseline.json"
    link.symlink_to(target)

    with pytest.raises(BaselineError, match="regular file"):
        write_baseline_atomic(
            tmp_path,
            Path(".agent-maintainer/contracts-baseline.json"),
            _baseline(),
        )


def test_failed_atomic_replace_preserves_existing_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed replace leaves the old exact destination bytes untouched."""
    relative = Path(".agent-maintainer/contracts-baseline.json")
    destination = tmp_path / relative
    destination.parent.mkdir()
    destination.write_text("old-baseline\n", encoding="utf-8")

    def fail_replace(_source: str, _destination: Path) -> None:
        raise OSError("synthetic replace failure")

    monkeypatch.setattr(baseline_write.os, "replace", fail_replace)

    with pytest.raises(BaselineError, match="atomically write"):
        write_baseline_atomic(tmp_path, relative, _baseline())

    assert destination.read_text(encoding="utf-8") == "old-baseline\n"
    assert list(destination.parent.glob(f".{destination.name}.*")) == []
