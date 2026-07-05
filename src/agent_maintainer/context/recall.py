"""File-backed recall ledger for compaction-safe context."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LEDGER_DIR = "context"
LEDGER_FILE = "ledger.jsonl"
DEFAULT_RECALL_LIMIT = 10
ITEM_ID_LENGTH = 12
VALID_KINDS = frozenset(
    (
        "artifact",
        "constraint",
        "decision",
        "failure",
        "summary",
        "task",
        "value",
    ),
)


@dataclass(frozen=True)
class RecallItem:
    """One compaction-safe recall ledger item."""

    item_id: str
    created_at: str
    kind: str
    summary: str
    paths: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    values: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecallInput:
    """Input used to append one recall ledger item."""

    kind: str
    summary: str
    paths: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    values: tuple[str, ...] = ()


def ledger_path(log_dir: Path) -> Path:
    """Return the recall ledger path for a verification log directory."""
    return log_dir / LEDGER_DIR / LEDGER_FILE


def add_item(log_dir: Path, item_input: RecallInput) -> RecallItem:
    """Append one item to the recall ledger."""
    normalized_kind = normalize_kind(item_input.kind)
    clean_summary = item_input.summary.strip()
    if not clean_summary:
        raise ValueError("summary is required")

    created_at = datetime.now(tz=UTC).isoformat(timespec="seconds")
    item = RecallItem(
        item_id=make_item_id(normalized_kind, clean_summary, created_at),
        created_at=created_at,
        kind=normalized_kind,
        summary=clean_summary,
        paths=clean_tuple(item_input.paths),
        artifacts=clean_tuple(item_input.artifacts),
        commands=clean_tuple(item_input.commands),
        tags=clean_tuple(item_input.tags),
        values=clean_tuple(item_input.values),
    )
    path = ledger_path(log_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as ledger_file:
        ledger_file.write(json.dumps(item_to_json(item), sort_keys=True))
        ledger_file.write("\n")
    return item


def recall_items(
    log_dir: Path,
    *,
    kind: str | None = None,
    query: str | None = None,
    limit: int = DEFAULT_RECALL_LIMIT,
) -> list[RecallItem]:
    """Return newest ledger items matching the requested filters."""
    normalized_kind = normalize_kind(kind) if kind else None
    clean_query = query.strip().lower() if query else None
    matches = [
        item
        for item in read_items(log_dir)
        if item_matches(item, kind=normalized_kind, query=clean_query)
    ]
    return list(reversed(matches))[:limit]


def read_items(log_dir: Path) -> list[RecallItem]:
    """Read all valid recall ledger items."""
    path = ledger_path(log_dir)
    if not path.exists():
        return []
    items: list[RecallItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        items.append(item_from_json(json.loads(line)))
    return items


def render_item_text(item: RecallItem) -> str:
    """Render one item after an add command."""
    return "\n".join(
        (
            "Recall ledger item added",
            f"id: {item.item_id}",
            f"kind: {item.kind}",
            f"summary: {item.summary}",
        ),
    )


def render_recall_text(items: list[RecallItem]) -> str:
    """Render bounded recall results for agent-facing output."""
    if not items:
        return "No recall ledger items found."
    lines = ["Context recall"]
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. [{item.kind}] {item.summary}")
        lines.append(f"   id: {item.item_id}")
        append_optional_line(lines, "paths", item.paths)
        append_optional_line(lines, "artifacts", item.artifacts)
        append_optional_line(lines, "rehydrate", item.commands)
        append_optional_line(lines, "tags", item.tags)
        append_optional_line(lines, "values", item.values)
    return "\n".join(lines)


def render_items_json(items: list[RecallItem]) -> str:
    """Render recall items as JSON."""
    return json.dumps({"items": [item_to_json(item) for item in items]}, indent=2)


def render_item_json(item: RecallItem) -> str:
    """Render one item as JSON."""
    return json.dumps(item_to_json(item), indent=2)


def append_optional_line(
    lines: list[str],
    label: str,
    values: tuple[str, ...],
) -> None:
    """Append a compact values line when values exist."""
    if values:
        joined_values = ", ".join(values)
        lines.append(f"   {label}: {joined_values}")


def normalize_kind(kind: str) -> str:
    """Return a validated recall item kind."""
    normalized = kind.strip().lower()
    if normalized not in VALID_KINDS:
        expected = ", ".join(sorted(VALID_KINDS))
        raise ValueError(f"kind must be one of: {expected}")
    return normalized


def clean_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    """Drop blank repeated CLI values."""
    return tuple(value.strip() for value in values if value.strip())


def item_matches(
    item: RecallItem,
    *,
    kind: str | None,
    query: str | None,
) -> bool:
    """Return whether item matches filters."""
    if kind and item.kind != kind:
        return False
    if not query:
        return True
    return query in searchable_text(item)


def searchable_text(item: RecallItem) -> str:
    """Return lower-cased text used by simple query filters."""
    parts = (
        item.kind,
        item.summary,
        *item.paths,
        *item.artifacts,
        *item.commands,
        *item.tags,
        *item.values,
    )
    return "\n".join(parts).lower()


def make_item_id(kind: str, summary: str, created_at: str) -> str:
    """Return compact stable-looking identifier for one ledger append."""
    digest = hashlib.sha256(f"{kind}\n{summary}\n{created_at}".encode()).hexdigest()
    return digest[:ITEM_ID_LENGTH]


def item_to_json(item: RecallItem) -> dict[str, Any]:
    """Return JSON-serializable item payload."""
    return asdict(item)


def item_from_json(payload: dict[str, Any]) -> RecallItem:
    """Return item from JSON payload."""
    return RecallItem(
        item_id=str(payload["item_id"]),
        created_at=str(payload["created_at"]),
        kind=normalize_kind(str(payload["kind"])),
        summary=str(payload["summary"]),
        paths=tuple(payload.get("paths", ())),
        artifacts=tuple(payload.get("artifacts", ())),
        commands=tuple(payload.get("commands", ())),
        tags=tuple(payload.get("tags", ())),
        values=tuple(payload.get("values", ())),
    )
