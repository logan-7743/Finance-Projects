"""Streaming JSONL storage — one record per line, no full-corpus loads."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from quant.events.schema import EventRecord


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def append_event_jsonl(path: Path, record: EventRecord) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record.to_json_dict(), ensure_ascii=False))
        handle.write("\n")


def iter_events_jsonl(path: Path) -> Iterator[EventRecord]:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            yield EventRecord.from_json_dict(json.loads(stripped))


def load_seen_ids(path: Path) -> set[str]:
    return {record.event_id for record in iter_events_jsonl(path)}
