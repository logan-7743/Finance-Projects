"""Ingest Trump social posts from trump.fm (Truth Social + X archive)."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from quant.events.paths import normalized_path, raw_dir
from quant.events.schema import EventRecord
from quant.events.store import append_event_jsonl, load_seen_ids

TRUMP_FM_BASE = "https://trump.fm/api/posts"
DEFAULT_PAGE_SIZE = 100
DEFAULT_SLEEP_SECONDS = 0.35
DEFAULT_MAX_RETRIES = 5


def parse_post_created_at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def post_to_event(post: dict[str, Any], *, include_reposts: bool = False) -> EventRecord | None:
    if post.get("isRepost") and not include_reposts:
        return None
    text = (post.get("content") or "").strip()
    if not text:
        return None
    created_at = post.get("createdAt")
    if not created_at:
        return None
    native_id = str(post.get("id") or post.get("platformId") or "")
    if not native_id:
        return None
    platform = str(post.get("platform") or "unknown")
    return EventRecord(
        event_id=f"trump_fm:{native_id}",
        utc_timestamp=parse_post_created_at(created_at),
        source="trump_fm",
        event_type="social_post",
        text=text,
        url=f"https://trump.fm/post/{native_id}" if native_id else None,
        native_id=native_id,
        metadata={
            "platform": platform,
            "platform_id": post.get("platformId"),
            "is_repost": bool(post.get("isRepost")),
            "deleted_at": post.get("deletedAt"),
            "external_metrics": post.get("externalMetrics"),
        },
    )


def fetch_page(
    client: httpx.Client,
    *,
    limit: int,
    cursor: str | None,
) -> dict[str, Any]:
    params: dict[str, str | int] = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    response = client.get(TRUMP_FM_BASE, params=params)
    response.raise_for_status()
    return response.json()


def pull_trump_fm(
    *,
    since: datetime,
    until: datetime | None = None,
    output_path: Path | None = None,
    raw_pages_dir: Path | None = None,
    include_reposts: bool = False,
    page_size: int = DEFAULT_PAGE_SIZE,
    sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
) -> dict[str, Any]:
    """Backfill social posts from trump.fm into JSONL (streaming, low memory)."""
    since = since.astimezone(UTC)
    until = (until or datetime.now(tz=UTC)).astimezone(UTC)
    out = output_path or normalized_path("trump_social.jsonl")
    pages_dir = raw_pages_dir or raw_dir("trump_fm")
    pages_dir.mkdir(parents=True, exist_ok=True)

    seen = load_seen_ids(out)
    stats = {
        "source": "trump_fm",
        "since": since.isoformat(),
        "until": until.isoformat(),
        "pages_fetched": 0,
        "posts_seen": 0,
        "events_written": 0,
        "reposts_skipped": 0,
        "duplicates_skipped": 0,
        "empty_text_skipped": 0,
        "stopped_before_since": False,
        "platform_counts": {},
        "oldest_timestamp": None,
        "newest_timestamp": None,
        "failures": [],
    }

    cursor: str | None = None
    page_index = 0

    with httpx.Client(timeout=60.0, headers={"Accept": "application/json"}) as client:
        while True:
            payload: dict[str, Any] | None = None
            for attempt in range(DEFAULT_MAX_RETRIES):
                try:
                    payload = fetch_page(client, limit=page_size, cursor=cursor)
                    break
                except httpx.HTTPError as exc:
                    if attempt + 1 >= DEFAULT_MAX_RETRIES:
                        stats["failures"].append(str(exc))
                        raise
                    time.sleep(2**attempt)

            assert payload is not None
            stats["pages_fetched"] += 1
            page_index += 1
            page_file = pages_dir / f"page_{page_index:05d}.json"
            page_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            posts = payload.get("data") or []
            if not posts:
                break

            oldest_on_page: datetime | None = None
            for post in posts:
                stats["posts_seen"] += 1
                created_raw = post.get("createdAt")
                if not created_raw:
                    continue
                created = parse_post_created_at(created_raw)
                oldest_on_page = created if oldest_on_page is None else min(oldest_on_page, created)

                if created > until:
                    continue
                if created < since:
                    stats["stopped_before_since"] = True
                    continue

                event = post_to_event(post, include_reposts=include_reposts)
                if event is None:
                    if post.get("isRepost"):
                        stats["reposts_skipped"] += 1
                    else:
                        stats["empty_text_skipped"] += 1
                    continue
                if event.event_id in seen:
                    stats["duplicates_skipped"] += 1
                    continue

                platform = str(event.metadata.get("platform") or "unknown")
                stats["platform_counts"][platform] = stats["platform_counts"].get(platform, 0) + 1
                oldest_raw = stats["oldest_timestamp"]
                newest_raw = stats["newest_timestamp"]
                if oldest_raw is None or event.utc_timestamp < datetime.fromisoformat(
                    str(oldest_raw).replace("Z", "+00:00")
                ):
                    stats["oldest_timestamp"] = event.utc_timestamp.isoformat()
                if newest_raw is None or event.utc_timestamp > datetime.fromisoformat(
                    str(newest_raw).replace("Z", "+00:00")
                ):
                    stats["newest_timestamp"] = event.utc_timestamp.isoformat()

                append_event_jsonl(out, event)
                seen.add(event.event_id)
                stats["events_written"] += 1

            meta = payload.get("meta") or {}
            if stats["stopped_before_since"] and oldest_on_page and oldest_on_page < since:
                break
            if not meta.get("hasMore"):
                break
            next_cursor = meta.get("cursor")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = str(next_cursor)
            time.sleep(sleep_seconds)

    stats["output_path"] = str(out)
    return stats


def iter_trump_fm_events(
    *,
    since: datetime,
    until: datetime | None = None,
    include_reposts: bool = False,
) -> Iterator[EventRecord]:
    """Fetch events without persisting — useful for tests."""
    since = since.astimezone(UTC)
    until = (until or datetime.now(tz=UTC)).astimezone(UTC)
    cursor: str | None = None

    with httpx.Client(timeout=60.0, headers={"Accept": "application/json"}) as client:
        while True:
            payload = fetch_page(client, limit=10, cursor=cursor)
            posts = payload.get("data") or []
            if not posts:
                break
            for post in posts:
                created_raw = post.get("createdAt")
                if not created_raw:
                    continue
                created = parse_post_created_at(created_raw)
                if created < since:
                    return
                if created > until:
                    continue
                event = post_to_event(post, include_reposts=include_reposts)
                if event:
                    yield event
            meta = payload.get("meta") or {}
            if not meta.get("hasMore"):
                break
            cursor = meta.get("cursor")
            if not cursor:
                break
