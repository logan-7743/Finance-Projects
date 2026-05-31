"""Ingest official White House remarks and presidential briefings (speech text)."""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from quant.events.paths import normalized_path, raw_dir
from quant.events.schema import EventRecord
from quant.events.store import append_event_jsonl, load_seen_ids

BASE_URL = "https://www.whitehouse.gov"
POST_SITEMAP_URL = "https://www.whitehouse.gov/post-sitemap.xml"
LISTING_PATHS = (
    "/remarks/",
    "/briefings-statements/",
)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
LINK_PATTERN = re.compile(
    r'href="(https://www\.whitehouse\.gov/(?:remarks|briefings-statements)/(\d{4})/(\d{2})/[^"]+)"'
)
SITEMAP_URL_PATTERN = re.compile(
    r"<loc>(https://www\.whitehouse\.gov/(?:remarks|briefings-statements)/(\d{4})/(\d{2})/[^<]+)</loc>"
)
DATE_PUBLISHED_PATTERN = re.compile(r'"datePublished"\s*:\s*"([^"]+)"')
TITLE_PATTERN = re.compile(r"<title>([^<]+)</title>", re.IGNORECASE)
CONTENT_START = '<div class="entry-content wp-block-post-content'
CONTENT_END = '<div class="entry-footer'


def parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def extract_article_links(html: str) -> list[tuple[str, int, int]]:
    seen: set[str] = set()
    links: list[tuple[str, int, int]] = []
    for match in LINK_PATTERN.finditer(html):
        url = match.group(1)
        year = int(match.group(2))
        month = int(match.group(3))
        if url in seen:
            continue
        seen.add(url)
        links.append((url, year, month))
    return links


def extract_sitemap_links(xml_text: str, *, since: datetime) -> list[str]:
    seen: set[str] = set()
    links: list[str] = []
    month_floor = datetime(since.year, since.month, 1, tzinfo=UTC)
    for match in SITEMAP_URL_PATTERN.finditer(xml_text):
        url = match.group(1)
        approx = datetime(int(match.group(2)), int(match.group(3)), 1, tzinfo=UTC)
        if approx < month_floor or url in seen:
            continue
        seen.add(url)
        links.append(url)
    return links


def extract_article_body(html: str) -> str:
    start = html.find(CONTENT_START)
    if start < 0:
        return ""
    end = html.find(CONTENT_END, start)
    chunk = html[start:end] if end > start else html[start:]
    chunk = re.sub(r"<script[\s\S]*?</script>", " ", chunk, flags=re.IGNORECASE)
    chunk = re.sub(r"<style[\s\S]*?</style>", " ", chunk, flags=re.IGNORECASE)
    chunk = re.sub(r"<[^>]+>", " ", chunk)
    chunk = unescape(chunk)
    chunk = re.sub(r"\s+", " ", chunk).strip()
    return chunk


def extract_title(html: str) -> str | None:
    match = TITLE_PATTERN.search(html)
    if not match:
        return None
    title = unescape(match.group(1)).strip()
    return title.removesuffix(" – The White House").strip()


def extract_published_at(html: str) -> datetime | None:
    match = DATE_PUBLISHED_PATTERN.search(html)
    if not match:
        return None
    return parse_iso_datetime(match.group(1))


def is_trump_speech(title: str | None, url: str, text: str) -> bool:
    haystack = " ".join(filter(None, [title, url, text[:500]])).lower()
    if "first lady" in haystack or "melania" in haystack:
        return False
    if "/remarks/" in url:
        return True
    trump_markers = (
        "president trump",
        "president donald",
        "donald j. trump",
        "remarks by president",
        "address by president",
    )
    return any(marker in haystack for marker in trump_markers)


def article_to_event(url: str, html: str) -> EventRecord | None:
    text = extract_article_body(html)
    if len(text) < 80:
        return None
    title = extract_title(html)
    if not is_trump_speech(title, url, text):
        return None
    published = extract_published_at(html)
    if published is None:
        return None
    slug = url.rstrip("/").split("/")[-1]
    native_id = slug
    return EventRecord(
        event_id=f"whitehouse:{native_id}",
        utc_timestamp=published,
        source="whitehouse",
        event_type="speech_transcript",
        text=text,
        url=url,
        native_id=native_id,
        metadata={"title": title, "word_count": len(text.split())},
    )


def fetch_text(client: httpx.Client, url: str) -> str:
    response = client.get(url)
    response.raise_for_status()
    return response.text


def discover_listing_pages(
    client: httpx.Client,
    listing_path: str,
    *,
    since: datetime,
    max_pages: int = 80,
) -> list[str]:
    since = since.astimezone(UTC)
    article_urls: list[str] = []
    seen_pages: set[str] = set()

    for page_num in range(1, max_pages + 1):
        page_url = urljoin(BASE_URL, listing_path if page_num == 1 else f"{listing_path}page/{page_num}/")
        if page_url in seen_pages:
            break
        seen_pages.add(page_url)
        try:
            html = fetch_text(client, page_url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404 and page_num > 1:
                break
            raise
        links = extract_article_links(html)
        if not links:
            break

        in_window = False
        for url, year, month in links:
            approx = datetime(year, month, 1, tzinfo=UTC)
            if approx >= datetime(since.year, since.month, 1, tzinfo=UTC):
                in_window = True
                article_urls.append(url)
            elif year < since.year or (year == since.year and month < since.month):
                continue

        oldest = min(links, key=lambda item: (item[1], item[2]))
        if oldest[1] < since.year or (oldest[1] == since.year and oldest[2] < since.month):
            break
        if not in_window and page_num > 3:
            break
        time.sleep(0.4)

    return list(dict.fromkeys(article_urls))


def discover_sitemap_articles(client: httpx.Client, *, since: datetime) -> list[str]:
    xml_text = fetch_text(client, POST_SITEMAP_URL)
    return extract_sitemap_links(xml_text, since=since)


def pull_whitehouse(
    *,
    since: datetime,
    until: datetime | None = None,
    output_path: Path | None = None,
    raw_dir_path: Path | None = None,
) -> dict[str, Any]:
    since = since.astimezone(UTC)
    until = (until or datetime.now(tz=UTC)).astimezone(UTC)
    out = output_path or normalized_path("trump_speeches.jsonl")
    raw_base = raw_dir_path or raw_dir("whitehouse")
    raw_base.mkdir(parents=True, exist_ok=True)

    seen = load_seen_ids(out)
    stats: dict[str, Any] = {
        "source": "whitehouse",
        "since": since.isoformat(),
        "until": until.isoformat(),
        "listing_paths": list(LISTING_PATHS),
        "urls_discovered": 0,
        "articles_fetched": 0,
        "events_written": 0,
        "skipped_out_of_window": 0,
        "skipped_not_trump": 0,
        "skipped_short_text": 0,
        "duplicates_skipped": 0,
        "failures": [],
        "oldest_timestamp": None,
        "newest_timestamp": None,
    }

    headers = {"User-Agent": USER_AGENT, "Accept": "text/html"}
    with httpx.Client(timeout=60.0, headers=headers, follow_redirects=True) as client:
        article_urls: list[str] = []
        try:
            article_urls.extend(discover_sitemap_articles(client, since=since))
        except httpx.HTTPError as exc:
            stats["failures"].append(f"{POST_SITEMAP_URL}: {exc}")
            for listing_path in LISTING_PATHS:
                try:
                    article_urls.extend(discover_listing_pages(client, listing_path, since=since))
                except httpx.HTTPError as listing_exc:
                    stats["failures"].append(f"{listing_path}: {listing_exc}")

        article_urls = list(dict.fromkeys(article_urls))
        stats["urls_discovered"] = len(article_urls)

        for index, url in enumerate(article_urls, start=1):
            slug = url.rstrip("/").split("/")[-1]
            raw_file = raw_base / f"{index:05d}_{slug}.html"
            try:
                if raw_file.exists():
                    html = raw_file.read_text(encoding="utf-8")
                else:
                    html = fetch_text(client, url)
                    raw_file.write_text(html, encoding="utf-8")
                stats["articles_fetched"] += 1
            except httpx.HTTPError as exc:
                stats["failures"].append(f"{url}: {exc}")
                continue

            event = article_to_event(url, html)
            if event is None:
                published = extract_published_at(html)
                if published and (published < since or published > until):
                    stats["skipped_out_of_window"] += 1
                elif len(extract_article_body(html)) < 80:
                    stats["skipped_short_text"] += 1
                else:
                    stats["skipped_not_trump"] += 1
                continue
            if event.utc_timestamp < since or event.utc_timestamp > until:
                stats["skipped_out_of_window"] += 1
                continue
            if event.event_id in seen:
                stats["duplicates_skipped"] += 1
                continue

            append_event_jsonl(out, event)
            seen.add(event.event_id)
            stats["events_written"] += 1
            if stats["oldest_timestamp"] is None or event.utc_timestamp < parse_iso_datetime(
                stats["oldest_timestamp"]
            ):
                stats["oldest_timestamp"] = event.utc_timestamp.isoformat()
            if stats["newest_timestamp"] is None or event.utc_timestamp > parse_iso_datetime(
                stats["newest_timestamp"]
            ):
                stats["newest_timestamp"] = event.utc_timestamp.isoformat()
            time.sleep(0.35)

    stats["output_path"] = str(out)
    return stats
