"""Coverage report for the local event corpus."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from quant.events.store import iter_events_jsonl


def summarize_jsonl(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"path": str(path), "exists": False, "count": 0}

    count = 0
    by_source: Counter[str] = Counter()
    by_month: Counter[str] = Counter()
    oldest: datetime | None = None
    newest: datetime | None = None

    for record in iter_events_jsonl(path):
        count += 1
        by_source[record.source] += 1
        month_key = record.utc_timestamp.astimezone(UTC).strftime("%Y-%m")
        by_month[month_key] += 1
        oldest = record.utc_timestamp if oldest is None else min(oldest, record.utc_timestamp)
        newest = record.utc_timestamp if newest is None else max(newest, record.utc_timestamp)

    return {
        "path": str(path),
        "exists": True,
        "count": count,
        "by_source": dict(by_source),
        "by_month": dict(sorted(by_month.items())),
        "oldest": oldest.isoformat() if oldest else None,
        "newest": newest.isoformat() if newest else None,
    }


def merge_jsonl_files(sources: list[Path], destination: Path) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()

    seen: set[str] = set()
    written = 0
    duplicates = 0

    from quant.events.store import append_event_jsonl

    for source in sources:
        if not source.exists():
            continue
        for record in iter_events_jsonl(source):
            if record.event_id in seen:
                duplicates += 1
                continue
            append_event_jsonl(destination, record)
            seen.add(record.event_id)
            written += 1

    return {
        "destination": str(destination),
        "written": written,
        "duplicates_skipped": duplicates,
        "summary": summarize_jsonl(destination),
    }
