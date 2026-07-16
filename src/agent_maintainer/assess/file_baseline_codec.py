"""Bounded canonical codec for provider-neutral file ceiling baselines."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from agent_maintainer.assess import file_baseline_state

MAX_BASELINE_BYTES = 2_000_000
MAX_BASELINE_ENTRIES = 20_000
ENTRY_FIELDS = frozenset(("group", "nonblank_ceiling", "path", "physical_ceiling"))


def render_baseline(baseline: file_baseline_state.FileCeilingBaseline) -> str:
    """Render canonical newline-terminated JSON."""
    payload = {
        "entries": [
            {
                "group": entry.group,
                "nonblank_ceiling": entry.nonblank_ceiling,
                "path": entry.path,
                "physical_ceiling": entry.physical_ceiling,
            }
            for entry in baseline.entries
        ],
        "source_commit": baseline.source_commit,
        "version": baseline.version,
    }
    return f"{json.dumps(payload, indent=2, sort_keys=True)}\n"


def parse_baseline(text: str) -> file_baseline_state.FileCeilingBaseline:
    """Parse one bounded strict file ceiling baseline document."""
    root, items = _parse_root(_decode_payload(text))
    return file_baseline_state.FileCeilingBaseline(
        _integer(root["version"], "version"),
        _string(root["source_commit"], "source_commit"),
        tuple(_parse_entry(item) for item in items),
    )


def _decode_payload(text: str) -> Any:
    if len(text.encode("utf-8")) > MAX_BASELINE_BYTES:
        raise ValueError("file ceiling baseline exceeds the size limit")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("file ceiling baseline is malformed JSON") from exc


def _parse_root(payload: Any) -> tuple[dict[str, Any], list[Any]]:
    root = _object(payload, "file ceiling baseline")
    if set(root) != {"entries", "source_commit", "version"}:
        raise ValueError("file ceiling baseline has unexpected fields")
    raw_entries = root["entries"]
    if not isinstance(raw_entries, list):
        raise ValueError("file ceiling baseline entries must be an array")
    items = cast(list[Any], raw_entries)
    if len(items) > MAX_BASELINE_ENTRIES:
        raise ValueError("file ceiling baseline contains too many entries")
    return root, items


def read_baseline(path: Path) -> file_baseline_state.FileCeilingBaseline:
    """Read one bounded file ceiling baseline."""
    if path.stat().st_size > MAX_BASELINE_BYTES:
        raise ValueError("file ceiling baseline exceeds the size limit")
    return parse_baseline(path.read_text(encoding="utf-8"))


def write_baseline(
    path: Path,
    baseline: file_baseline_state.FileCeilingBaseline,
    *,
    force: bool = False,
) -> None:
    """Write canonical JSON, refusing an unapproved overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if force else "x"
    try:
        with path.open(mode, encoding="utf-8", newline="\n") as handle:
            handle.write(render_baseline(baseline))
    except FileExistsError as exc:
        raise FileExistsError(f"baseline already exists: {path}") from exc


def _parse_entry(payload: Any) -> file_baseline_state.FileCeilingEntry:
    raw = _object(payload, "file ceiling entry")
    if frozenset(raw) != ENTRY_FIELDS:
        raise ValueError("file ceiling entry has unexpected fields")
    return file_baseline_state.FileCeilingEntry(
        _string(raw["group"], "entry.group"),
        _string(raw["path"], "entry.path"),
        _integer(raw["physical_ceiling"], "entry.physical_ceiling"),
        _integer(raw["nonblank_ceiling"], "entry.nonblank_ceiling"),
    )


def _object(payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be an object")
    raw = cast(dict[object, Any], payload)
    if any(not isinstance(key, str) for key in raw):
        raise ValueError(f"{label} must use string keys")
    return cast(dict[str, Any], raw)


def _string(payload: Any, label: str) -> str:
    if not isinstance(payload, str):
        raise ValueError(f"{label} must be a string")
    return payload


def _integer(payload: Any, label: str) -> int:
    if not isinstance(payload, int) or isinstance(payload, bool):
        raise ValueError(f"{label} must be an integer")
    return payload
